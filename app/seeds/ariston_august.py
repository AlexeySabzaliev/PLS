"""Демо-данные Аристон / Стрельна / август (из эталонного Excel Billings)."""
from __future__ import annotations

import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from app.db import db
from app.modules.processes.schema_resolver import ProcessLine, ProcessLineConfig
from app.modules.processes.templates import EXAMPLE_LINE_CONFIGS
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Warehouse,
)
from app.modules.uss.models import OperationDailyTotal, ShiftReport, VehicleOperation
from app.seeds.ariston_tariffs import ensure_ariston_billing_rates, ensure_ariston_tariffs
from app.seeds.billing_excel_ref import read_billing_reference, read_prr_rows

CONTRACT_NUMBER = "STR-OH-ARISTON"
AMENDMENT_NUMBER = "ДС-01/2025"
WAREHOUSE_CODE = "strelna"
YEAR = 2026
MONTH = 8


def resolve_august_excel_path() -> Path | None:
  """Путь к Ariston billing 08.2026.xlsx."""
  raw = (os.getenv("ARISTON_AUGUST_EXCEL") or os.getenv("ARISTON_BILLING_FIXTURES_PATH") or "").strip()
  if raw:
    p = Path(raw)
    if p.is_file():
      return p
    candidate = p / "Ariston billing 08.2026.xlsx"
    if candidate.is_file():
      return candidate
  for candidate in (
    Path(r"D:\Billings\backend\tests\fixtures\august\Ariston billing 08.2026.xlsx"),
    Path(__file__).resolve().parents[2] / "tests/fixtures/ariston_billing/Ariston billing 08.2026.xlsx",
  ):
    if candidate.is_file():
      return candidate
  return None


def _to_date(value) -> date | None:
  if value is None:
    return None
  if isinstance(value, datetime):
    return value.date()
  if isinstance(value, date):
    return value
  return date.fromisoformat(str(value)[:10])


def _to_dt(day: date, value) -> datetime | None:
  if value is None:
    return None
  if isinstance(value, datetime):
    return value.replace(year=day.year, month=day.month, day=day.day)
  if isinstance(value, time):
    return datetime.combine(day, value)
  s = str(value).strip()
  for fmt in ("%H:%M:%S", "%H:%M"):
    try:
      return datetime.combine(day, datetime.strptime(s, fmt).time())
    except ValueError:
      continue
  return None


def _dec(value) -> Decimal:
  if value is None or value == "" or value == "-":
    return Decimal("0")
  try:
    return Decimal(str(value).replace(",", "."))
  except Exception:
    return Decimal("0")


def _norm_plate(raw: str | None) -> str:
  s = str(raw or "").strip().replace("//", "/")
  return s[:32] if s else "—"


def _handling(op_type: str | None) -> str:
  t = (op_type or "").lower()
  if "приём" in t or "прием" in t:
    return "inbound"
  if "отгруз" in t:
    return "outbound"
  return "other"


def _distribute(total: int, days: list[date]) -> dict[date, int]:
  if not days or total <= 0:
    return {}
  days = sorted(set(days))
  base, rem = divmod(total, len(days))
  return {d: base + (1 if i < rem else 0) for i, d in enumerate(days)}


def _clear_august_ops(contract_id: int, warehouse_id: int) -> None:
  start, end = date(YEAR, MONTH, 1), date(YEAR, MONTH, 31)
  VehicleOperation.query.filter(
    VehicleOperation.contract_id == contract_id,
    VehicleOperation.warehouse_id == warehouse_id,
    VehicleOperation.operation_date >= start,
    VehicleOperation.operation_date <= end,
  ).delete(synchronize_session=False)
  OperationDailyTotal.query.filter(
    OperationDailyTotal.contract_id == contract_id,
    OperationDailyTotal.warehouse_id == warehouse_id,
    OperationDailyTotal.report_date >= start,
    OperationDailyTotal.report_date <= end,
  ).delete(synchronize_session=False)
  ShiftReport.query.filter(
    ShiftReport.warehouse_id == warehouse_id,
    ShiftReport.report_date >= start,
    ShiftReport.report_date <= end,
  ).delete(synchronize_session=False)


def _apply_vehicle_billing_extras(
  contract_id: int,
  warehouse_id: int,
  billing_lines: dict,
) -> None:
  """Распределить доп. комплекты и ELCO по ТС (для сверки с Excel)."""
  extra_total = int(billing_lines.get("extra_vehicle_docs", {}).get("qty", 0))
  elco_total = int(billing_lines.get("elco_passports", {}).get("qty", 0))
  if extra_total <= 0 and elco_total <= 0:
    return
  vehicles = (
    VehicleOperation.query.filter_by(contract_id=contract_id, warehouse_id=warehouse_id)
    .order_by(VehicleOperation.operation_date, VehicleOperation.id)
    .all()
  )
  if not vehicles:
    return
  if extra_total > 0:
    base, rem = divmod(extra_total, len(vehicles))
    for i, v in enumerate(vehicles):
      v.extra_document_set_qty = base + (1 if i < rem else 0)
  for i, v in enumerate(vehicles):
    if i >= elco_total:
      break
    rq = dict(v.report_quantities or {})
    rq["elco_passports"] = 1
    v.report_quantities = rq


def seed_ariston_strelna_august(*, verbose: bool = False, excel_path: Path | None = None) -> dict:
  """
  Аристон, склад Стрельна, август 2026 — как в Billings (ПРР + суточные + УЗ).
  Требует Excel: Ariston billing 08.2026.xlsx (см. ARISTON_AUGUST_EXCEL).
  """
  stats = {
    "excel": None,
    "vehicles": 0,
    "daily_lines": 0,
    "shift_days": 0,
    "billing_total": None,
  }

  path = excel_path or resolve_august_excel_path()
  if not path:
    raise FileNotFoundError(
      "Нет файла Ariston billing 08.2026.xlsx. "
      "Укажите ARISTON_AUGUST_EXCEL или скопируйте из Billings/tests/fixtures/august/"
    )
  stats["excel"] = str(path)

  wh = Warehouse.query.filter_by(code=WAREHOUSE_CODE).first()
  pt = ProductType.query.filter_by(code="RESPONSIBLE_STORAGE").first()
  if not wh or not pt:
    raise RuntimeError("Сначала flask pls seed-reference")

  client = Client.query.filter_by(name="Аристон").first()
  if not client:
    client = Client(name="Аристон", is_active=True)
    db.session.add(client)
    db.session.flush()

  contract = Contract.query.filter_by(number=CONTRACT_NUMBER, warehouse_id=wh.id).first()
  if not contract:
    contract = Contract(
      client_id=client.id,
      warehouse_id=wh.id,
      product_type_id=pt.id,
      number=CONTRACT_NUMBER,
      status="active",
    )
    db.session.add(contract)
    db.session.flush()

  am = ContractAmendment.query.filter_by(contract_id=contract.id, number=AMENDMENT_NUMBER).first()
  if not am:
    am = ContractAmendment(
      contract_id=contract.id,
      number=AMENDMENT_NUMBER,
      status="active",
      effective_from=date(2025, 6, 1),
    )
    db.session.add(am)
    db.session.flush()

  ensure_ariston_tariffs(contract.id, am.id, valid_from=date(2025, 6, 1))
  ensure_ariston_billing_rates(contract.id)

  contract.billing_config = {
    "area_mode": "two_tier",
    "fixed_m2days": 9435,
    "fixed_storage_m2days": 9435,
  }

  line = ProcessLine.query.filter_by(code="ariston_standard").first()
  if not line:
    line = ProcessLine(
      code="ariston_standard",
      name="Аристон стандарт",
      base_process="warehouse_logistics",
      client_id=client.id,
      is_active=True,
    )
    db.session.add(line)
    db.session.flush()
  if not line.config:
    db.session.add(
      ProcessLineConfig(
        process_line_id=line.id,
        config_json=EXAMPLE_LINE_CONFIGS["ariston_standard"],
      )
    )

  billing_lines, billing_total, _two_tier = read_billing_reference(path, MONTH)
  stats["billing_total"] = str(billing_total) if billing_total else None

  _clear_august_ops(contract.id, wh.id)

  op_days: list[date] = []
  for raw in read_prr_rows(path):
    day = _to_date(raw.get("operation_date"))
    if not day or day.month != MONTH:
      continue
    plate = _norm_plate(raw.get("vehicle"))
    vol = _dec(raw.get("volume"))
    in_m = _dec(raw.get("in_manual")) + _dec(raw.get("in_mech"))
    out_m = _dec(raw.get("out_manual")) + _dec(raw.get("out_mech"))
    handling = _handling(raw.get("op_type"))
    if handling == "inbound" and vol == 0:
      vol = in_m
    elif handling == "outbound" and vol == 0:
      vol = out_m

    db.session.add(
      VehicleOperation(
        contract_id=contract.id,
        warehouse_id=wh.id,
        operation_date=day,
        plate_number=plate,
        volume_document_m3=vol,
        handling_type_code=handling,
        registered_at=_to_dt(day, raw.get("reg_time")),
        departed_at=_to_dt(day, raw.get("dep_time")),
        report_quantities={
          "inbound_manual_m3": float(_dec(raw.get("in_manual"))),
          "outbound_manual_m3": float(_dec(raw.get("out_manual"))),
          "inbound_mech_m3": float(_dec(raw.get("in_mech"))),
          "outbound_mech_m3": float(_dec(raw.get("out_mech"))),
        },
      )
    )
    stats["vehicles"] += 1
    op_days.append(day)

  valve_total = int(billing_lines.get("valve_gluing", {}).get("qty", 0))
  flue_total = int(billing_lines.get("flue_stickering", {}).get("qty", 0))
  repack_total = int(billing_lines.get("repack_units", {}).get("qty", 0))
  area_extra = int(billing_lines.get("storage_area_extra", {}).get("qty", 0))

  work_days = sorted(set(op_days)) or [date(YEAR, MONTH, d) for d in (3, 10, 17, 24, 31)]

  for day, qty in _distribute(valve_total, work_days).items():
    db.session.add(
      OperationDailyTotal(
        contract_id=contract.id,
        warehouse_id=wh.id,
        report_date=day,
        billing_line_code="valve_gluing",
        quantity=Decimal(qty),
      )
    )
    stats["daily_lines"] += 1

  for day, qty in _distribute(flue_total, work_days).items():
    db.session.add(
      OperationDailyTotal(
        contract_id=contract.id,
        warehouse_id=wh.id,
        report_date=day,
        billing_line_code="flue_stickering",
        quantity=Decimal(qty),
      )
    )
    stats["daily_lines"] += 1

  repack_by_day = _distribute(repack_total, work_days[-5:] if len(work_days) >= 5 else work_days)
  for i, day in enumerate(sorted(repack_by_day.keys())):
    repack_qty = repack_by_day[day]
    db.session.add(
      ShiftReport(
        warehouse_id=wh.id,
        report_date=day,
        area_entries={"storage_area_extra": area_extra} if area_extra else {},
        extra_entries={"repack_units": repack_qty},
      )
    )
    stats["shift_days"] += 1

  _apply_vehicle_billing_extras(contract.id, wh.id, billing_lines)

  db.session.commit()
  if verbose:
    print(
      f"seed-ariston-august: {stats['vehicles']} ТС, "
      f"{stats['daily_lines']} суточных, {stats['shift_days']} смен УЗ, "
      f"итого биллинг {stats['billing_total']}"
    )
  return stats
