"""Договоры смены на дату: ДС действует на день + договоры с уже введёнными данными."""

from __future__ import annotations



from datetime import date, timedelta



from app.db import db

from app.modules.reference.amendment_scope import (
    amendment_active_on_date,
    amendment_effective_from,
    allowed_amendment_statuses,
    amendments_for_contract_on_date,
    primary_amendment_for_contract_on_date,
)

from app.modules.reference.models import Client, Contract, ContractAmendment, ProductType

from app.modules.uss.models import OperationDailyTotal, ShiftReport, VehicleOperation



SHIFT_DATE_MIN_DAYS = 730





def shift_date_bounds() -> tuple[str, str]:

    """Разумные границы выбора даты в UI смен."""

    today = date.today()

    min_day = today - timedelta(days=SHIFT_DATE_MIN_DAYS)

    return min_day.isoformat(), today.isoformat()





def _base_contract_query(warehouse_id: int):

    return (

        Contract.query.join(ProductType)

        .join(Client)

        .filter(

            Contract.warehouse_id == warehouse_id,

            Contract.status == "active",

            ProductType.code == "RESPONSIBLE_STORAGE",

            Client.is_active.is_(True),

        )

    )





def _amendment_active_on(contract_id: int, day: date) -> bool:

    return bool(amendments_for_contract_on_date(contract_id, day))





def contracts_with_amendment_on_date(warehouse_id: int, day: date) -> list[Contract]:

    """Договоры с действующим ДС на указанную дату."""

    contracts = _base_contract_query(warehouse_id).all()

    matched = [c for c in contracts if _amendment_active_on(c.id, day)]

    return sorted(matched, key=lambda c: (c.client.name, c.number))





def contract_ids_with_vehicles(warehouse_id: int, day: date) -> list[int]:

    rows = (

        db.session.query(VehicleOperation.contract_id)

        .filter(

            VehicleOperation.warehouse_id == warehouse_id,

            VehicleOperation.operation_date == day,

        )

        .distinct()

        .all()

    )

    return [r[0] for r in rows]





def contract_ids_with_daily_totals(warehouse_id: int, day: date) -> list[int]:

    rows = (

        db.session.query(OperationDailyTotal.contract_id)

        .filter(

            OperationDailyTotal.warehouse_id == warehouse_id,

            OperationDailyTotal.report_date == day,

        )

        .distinct()

        .all()

    )

    return [r[0] for r in rows]





def contract_ids_with_shift_report_data(warehouse_id: int, day: date) -> list[int]:

    """Договоры склада, если за день уже есть сохранённые данные УЗ."""

    row = ShiftReport.query.filter_by(warehouse_id=warehouse_id, report_date=day).first()

    if not row:

        return []

    if not ((row.area_entries or {}) or (row.extra_entries or {})):

        return []

    return [c.id for c in _base_contract_query(warehouse_id).all()]





def merge_contracts(primary: list[Contract], extra_ids: list[int], warehouse_id: int) -> list[Contract]:

    """Объединить списки; подтянуть договоры по id (сохранённые строки за день)."""

    by_id = {c.id: c for c in primary}

    missing = [cid for cid in extra_ids if cid not in by_id]

    if missing:

        extra = (

            _base_contract_query(warehouse_id)

            .filter(Contract.id.in_(missing))

            .all()

        )

        for c in extra:

            by_id[c.id] = c

    return sorted(by_id.values(), key=lambda c: (c.client.name, c.number))





def contracts_for_transport_shift(warehouse_id: int, day: date) -> list[Contract]:

    primary = contracts_with_amendment_on_date(warehouse_id, day)

    extra_ids = contract_ids_with_vehicles(warehouse_id, day)

    return merge_contracts(primary, extra_ids, warehouse_id)





def contracts_for_warehouse_shift(warehouse_id: int, day: date) -> list[Contract]:

    primary = contracts_with_amendment_on_date(warehouse_id, day)

    extra_ids = contract_ids_with_daily_totals(warehouse_id, day)

    return merge_contracts(primary, extra_ids, warehouse_id)





def contracts_for_inventory_shift(warehouse_id: int, day: date) -> list[Contract]:

    primary = contracts_with_amendment_on_date(warehouse_id, day)

    extra_ids = contract_ids_with_shift_report_data(warehouse_id, day)

    return merge_contracts(primary, extra_ids, warehouse_id)





def contract_date_hint(contract_id: int, day: date) -> str | None:

    """Подсказка, если на дату нет действующего ДС."""

    if _amendment_active_on(contract_id, day):

        return None

    statuses = allowed_amendment_statuses()

    amendments = (

        ContractAmendment.query.filter(

            ContractAmendment.contract_id == contract_id,

            ContractAmendment.status.in_(statuses),

        )

        .all()

    )

    if not amendments:

        return "На дату нет активного доп. соглашения по договору."

    earliest = min(amendments, key=amendment_effective_from)

    eff_from = amendment_effective_from(earliest)

    if eff_from > day:

        return (

            f"На {day.isoformat()} нет действующего доп. соглашения. "

            f"Первое ДС с {eff_from.isoformat()}."

        )

    if earliest.status == "draft" and "draft" not in statuses:

        return "ДС в статусе «черновик» — активируйте перед вводом данных."

    return "На дату нет активного доп. соглашения по договору."





def format_shift_block_header(contract: Contract, amendment: ContractAmendment | None) -> str:
    """Заголовок блока смены: ДС в приоритете, договор вторично."""
    if amendment:
        eff = amendment_effective_from(amendment)
        return f"ДС №{amendment.number} (с {eff.strftime('%d.%m.%Y')}) · договор {contract.number}"
    return f"Договор {contract.number}"


def shift_block_key(contract_id: int, amendment_id: int | None) -> str:
    if amendment_id:
        return f"{contract_id}:{amendment_id}"
    return str(contract_id)


def serialize_shift_blocks(contracts: list[Contract], day: date) -> list[dict]:
    """Блоки смены: по одному на каждое действующее ДС; без ДС — один блок с подсказкой."""
    blocks: list[dict] = []
    for c in contracts:
        amendments = amendments_for_contract_on_date(c.id, day)
        if amendments:
            for am in amendments:
                blocks.append(
                    {
                        "id": c.id,
                        "contract_id": c.id,
                        "amendment_id": am.id,
                        "number": c.number,
                        "amendment_number": am.number,
                        "amendment_effective_from": amendment_effective_from(am).isoformat(),
                        "header": format_shift_block_header(c, am),
                        "block_key": shift_block_key(c.id, am.id),
                        "client_id": c.client_id,
                        "client_name": c.client.name if c.client else None,
                        "date_hint": None,
                    }
                )
        else:
            blocks.append(
                {
                    "id": c.id,
                    "contract_id": c.id,
                    "amendment_id": None,
                    "number": c.number,
                    "amendment_number": None,
                    "amendment_effective_from": None,
                    "header": format_shift_block_header(c, None),
                    "block_key": shift_block_key(c.id, None),
                    "client_id": c.client_id,
                    "client_name": c.client.name if c.client else None,
                    "date_hint": contract_date_hint(c.id, day),
                }
            )
    return blocks


def serialize_primary_shift_blocks(contracts: list[Contract], day: date) -> list[dict]:
    """Транспорт: один блок на договор/клиента — только основное ДС на дату."""
    blocks: list[dict] = []
    for c in contracts:
        am = primary_amendment_for_contract_on_date(c.id, day)
        if am:
            blocks.append(
                {
                    "id": c.id,
                    "contract_id": c.id,
                    "amendment_id": am.id,
                    "number": c.number,
                    "amendment_number": am.number,
                    "amendment_effective_from": amendment_effective_from(am).isoformat(),
                    "header": format_shift_block_header(c, am),
                    "block_key": shift_block_key(c.id, am.id),
                    "client_id": c.client_id,
                    "client_name": c.client.name if c.client else None,
                    "date_hint": None,
                }
            )
        else:
            blocks.append(
                {
                    "id": c.id,
                    "contract_id": c.id,
                    "amendment_id": None,
                    "number": c.number,
                    "amendment_number": None,
                    "amendment_effective_from": None,
                    "header": format_shift_block_header(c, None),
                    "block_key": shift_block_key(c.id, None),
                    "client_id": c.client_id,
                    "client_name": c.client.name if c.client else None,
                    "date_hint": contract_date_hint(c.id, day),
                }
            )
    return blocks


def serialize_contracts(contracts: list[Contract], day: date) -> list[dict]:
    return serialize_shift_blocks(contracts, day)

