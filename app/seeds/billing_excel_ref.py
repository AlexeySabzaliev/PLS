"""Чтение эталонных Excel биллинга Аристон (порт из Billings)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

NEW_LINE_MAP = {
    "1.1": "storage_area_fixed",
    "1.2": "storage_area_extra",
    "2": "manual_m3",
    "2.0": "manual_m3",
    "2.1": "extra_manual_m3",
    "3": "mechanized_m3",
    "3.0": "mechanized_m3",
    "4": "vehicle_docs",
    "4.0": "vehicle_docs",
    "4.1": "vehicle_docs",
    "4.2": "extra_vehicle_docs",
    "4.3": "elco_passports",
    "5": "repack_units",
    "5.0": "repack_units",
    "5.1": "repack_units",
    "5.2": "valve_gluing",
    "5.3": "flue_stickering",
    "6": "overtime_m3",
    "7": "inventory_hours",
    "8": "elco_drain_hours",
}


def read_billing_reference(
  path: Path, month: int,
) -> tuple[dict[str, dict], Decimal | None, bool]:
  """Лист Billing → {line_code: {qty, amount}}, итого, two_tier (июн+)."""
  line_map = NEW_LINE_MAP if month >= 6 else {
    "1": "storage_area",
    "2": "manual_m3",
    "3": "mechanized_m3",
    "4": "vehicle_docs",
    "5": "repack_units",
    "6": "overtime_m3",
    "7": "inventory_hours",
    "8": "elco_drain_hours",
  }
  wb = load_workbook(path, read_only=True, data_only=True)
  ws = wb["Billing"]
  lines: dict[str, dict] = {}
  total = None
  for row in ws.iter_rows(min_row=4, max_row=50, values_only=True):
    if not row:
      continue
    num = str(row[0]).strip() if row[0] is not None else ""
    code = line_map.get(num)
    if code:
      qty = Decimal(str(row[4])) if row[4] not in (None, "-", "") else Decimal("0")
      amt = Decimal(str(row[5])) if row[5] is not None else Decimal("0")
      prev = lines.get(code)
      if prev:
        qty += prev["qty"]
        amt += prev["amount"]
      lines[code] = {"qty": qty, "amount": amt, "num": num, "name": row[1]}
    if row[4] == "ИТОГО:" and row[5] is not None and total is None:
      total = Decimal(str(row[5]))
  wb.close()
  return lines, total, month >= 6


def read_prr_rows(path: Path) -> list[dict]:
  """Строки листа ПРР для импорта vehicle_operations."""
  wb = load_workbook(path, read_only=True, data_only=True)
  sheet = "ПРР" if "ПРР" in wb.sheetnames else wb.worksheets[1].title
  ws = wb[sheet]
  rows_iter = ws.iter_rows(values_only=True)
  header = next(rows_iter)
  col = {str(v).strip(): i for i, v in enumerate(header) if v}

  def idx(*names: str) -> int | None:
    for key, i in col.items():
      low = key.lower()
      if all(n.lower() in low for n in names):
        return i
    return None

  ix = {
    "operation_date": col.get("Дата отчета"),
    "waybill": col.get("Номер накладной"),
    "vehicle": col.get("Номер ТС:") or col.get("Номер ТС"),
    "op_type": col.get("Тип операции"),
    "volume": idx("объем", "документ") or col.get("Объем груза по документам (м³)"),
    "in_mech": idx("входящая", "механ") or col.get("Входящая поставка, механическая выгрузка, (м³)"),
    "in_manual": idx("входящая", "ручн") or col.get("Входящая поставка, ручная выгрузка, (м³)"),
    "out_mech": idx("исходящая", "механ") or col.get("Исходящая поставка, механизированная погрузка, (м³)"),
    "out_manual": idx("исходящая", "ручн") or col.get("Исходящая поставка, ручная погрузка, (м³)"),
    "reg_time": col.get("Время регистрации ТС в офисе:") or idx("регистрации", "тс"),
    "dep_time": col.get("Время убытия ТС:") or idx("убытия", "тс"),
    "torg2": col.get("№ акта ТОРГ-2"),
    "mx1": col.get("№ МХ-1"),
    "mx3": col.get("№ МХ-3"),
    "seal": col.get("№ пломбы"),
  }
  result: list[dict] = []
  for row in rows_iter:
    if not row or ix["operation_date"] is None or not row[ix["operation_date"]]:
      continue
    result.append({k: row[v] if v is not None else None for k, v in ix.items()})
  wb.close()
  return result
