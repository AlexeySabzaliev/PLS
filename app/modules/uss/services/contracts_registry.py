"""Свод договоров и доп. соглашений по клиентам."""
from __future__ import annotations

from datetime import date

from app.db import db
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Warehouse,
)

CONTRACT_STATUS_LABELS = {
    "active": "Действует",
    "suspended": "Приостановлен",
    "closed": "Закрыт",
    "draft": "Черновик",
}

AMENDMENT_STATUS_LABELS = {
    "draft": "Черновик",
    "active": "Действует",
    "superseded": "Заменено",
}


def _status_label(code: str | None, labels: dict[str, str]) -> str:
    if not code:
        return "—"
    return labels.get(code, code)


def _end_display(effective_to: date | None, auto_renew: bool) -> str:
    if auto_renew:
        return "∞"
    if effective_to is None:
        return "бессрочно"
    return effective_to.isoformat()


def _days_until_end(effective_to: date | None, auto_renew: bool, today: date) -> int | None:
    if auto_renew or effective_to is None:
        return None
    return (effective_to - today).days


def _expiring_soon(
    effective_to: date | None,
    auto_renew: bool,
    today: date,
    days: int,
) -> bool:
    if auto_renew or effective_to is None:
        return False
    return 0 <= (effective_to - today).days <= days


def _warehouse_ids_for_user(user: dict) -> list[int] | None:
    if user.get("is_admin"):
        return None
    return list(user.get("warehouse_ids") or [])


def _row(
    *,
    warehouse: Warehouse,
    client: Client,
    contract: Contract,
    product_type: ProductType | None,
    amendment: ContractAmendment | None,
    today: date,
    expiring_days: int,
) -> dict:
    auto_renew = bool(
        amendment.auto_renew if amendment is not None else contract.auto_renew
    )
    effective_from = amendment.effective_from.isoformat() if amendment and amendment.effective_from else None
    effective_to = amendment.effective_to if amendment else None
    end_display = _end_display(effective_to, auto_renew)
    days_left = _days_until_end(effective_to, auto_renew, today)
    am_status = amendment.status if amendment else None

    return {
        "warehouse_id": warehouse.id,
        "warehouse_code": warehouse.code,
        "warehouse_name": warehouse.name,
        "client_id": client.id,
        "client_name": client.name,
        "contract_id": contract.id,
        "contract_number": contract.number,
        "contract_status": contract.status,
        "contract_status_label": _status_label(contract.status, CONTRACT_STATUS_LABELS),
        "contract_auto_renew": bool(contract.auto_renew),
        "product_type": product_type.name if product_type else None,
        "amendment_id": amendment.id if amendment else None,
        "amendment_number": amendment.number if amendment else None,
        "amendment_status": am_status,
        "amendment_status_label": _status_label(am_status, AMENDMENT_STATUS_LABELS) if amendment else "—",
        "effective_from": effective_from,
        "effective_to": effective_to.isoformat() if effective_to else None,
        "auto_renew": auto_renew,
        "end_display": end_display,
        "days_until_end": days_left,
        "expiring_soon": _expiring_soon(effective_to, auto_renew, today, expiring_days),
    }


def build_contracts_registry_report(
    user: dict,
    *,
    warehouse_id: int | None = None,
    expiring_days: int = 90,
    status_filter: str = "all",
) -> dict:
    """Свод договоров и ДС, сгруппированный по клиентам."""
    today = date.today()
    expiring_days = max(1, min(expiring_days, 365))

    wh_ids = _warehouse_ids_for_user(user)
    if wh_ids is not None and not wh_ids:
        return _empty_report(today, warehouse_id, expiring_days)

    q = (
        db.session.query(Contract, Client, Warehouse, ProductType)
        .join(Client, Client.id == Contract.client_id)
        .join(Warehouse, Warehouse.id == Contract.warehouse_id)
        .join(ProductType, ProductType.id == Contract.product_type_id)
        .order_by(Client.name, Contract.number, Contract.id)
    )
    if warehouse_id is not None:
        q = q.filter(Contract.warehouse_id == warehouse_id)
    elif wh_ids is not None:
        q = q.filter(Contract.warehouse_id.in_(wh_ids))

    contracts = q.all()
    contract_ids = [c.id for c, *_ in contracts]
    amendments_by_contract: dict[int, list[ContractAmendment]] = {cid: [] for cid in contract_ids}
    if contract_ids:
        for am in (
            ContractAmendment.query.filter(ContractAmendment.contract_id.in_(contract_ids))
            .order_by(ContractAmendment.effective_from.desc(), ContractAmendment.id.desc())
            .all()
        ):
            amendments_by_contract[am.contract_id].append(am)

    flat_rows: list[dict] = []
    for contract, client, warehouse, product_type in contracts:
        amendments = amendments_by_contract.get(contract.id) or []
        if amendments:
            for am in amendments:
                flat_rows.append(
                    _row(
                        warehouse=warehouse,
                        client=client,
                        contract=contract,
                        product_type=product_type,
                        amendment=am,
                        today=today,
                        expiring_days=expiring_days,
                    )
                )
        else:
            flat_rows.append(
                _row(
                    warehouse=warehouse,
                    client=client,
                    contract=contract,
                    product_type=product_type,
                    amendment=None,
                    today=today,
                    expiring_days=expiring_days,
                )
            )

    if status_filter == "active_contract":
        flat_rows = [r for r in flat_rows if r["contract_status"] == "active"]
    elif status_filter == "active_amendment":
        flat_rows = [r for r in flat_rows if r["amendment_status"] == "active"]
    elif status_filter == "expiring":
        flat_rows = [r for r in flat_rows if r["expiring_soon"]]

    flat_rows.sort(
        key=lambda r: (
            0 if r["expiring_soon"] else 1,
            r["days_until_end"] if r["days_until_end"] is not None else 99999,
            r["client_name"].lower(),
            r["contract_number"],
            r["amendment_number"] or "",
        )
    )

    clients_map: dict[int, dict] = {}
    for row in flat_rows:
        cid = row["client_id"]
        clients_map.setdefault(
            cid,
            {
                "client_id": cid,
                "client_name": row["client_name"],
                "rows": [],
            },
        )
        clients_map[cid]["rows"].append(row)

    contract_ids_seen = {r["contract_id"] for r in flat_rows}
    amendment_ids_seen = {r["amendment_id"] for r in flat_rows if r["amendment_id"]}

    summary = {
        "contracts_total": len(contract_ids_seen),
        "amendments_total": len(amendment_ids_seen),
        "expiring_soon": sum(1 for r in flat_rows if r["expiring_soon"]),
        "auto_renew": sum(1 for r in flat_rows if r["auto_renew"]),
        "by_contract_status": _count_by(flat_rows, "contract_status", CONTRACT_STATUS_LABELS),
        "by_amendment_status": _count_by(flat_rows, "amendment_status", AMENDMENT_STATUS_LABELS),
    }

    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code)
    if warehouse_id is not None:
        warehouses = warehouses.filter(Warehouse.id == warehouse_id)
    elif wh_ids is not None:
        warehouses = warehouses.filter(Warehouse.id.in_(wh_ids))

    return {
        "generated_at": today.isoformat(),
        "warehouse_id": warehouse_id,
        "expiring_days": expiring_days,
        "status_filter": status_filter,
        "summary": summary,
        "clients": list(clients_map.values()),
        "warehouses": [
            {"id": w.id, "code": w.code, "name": w.name} for w in warehouses.all()
        ],
    }


def _count_by(rows: list[dict], field: str, labels: dict[str, str]) -> list[dict]:
    counts: dict[str | None, int] = {}
    for row in rows:
        key = row.get(field)
        counts[key] = counts.get(key, 0) + 1
    out = []
    for code, count in sorted(counts.items(), key=lambda x: (x[0] is None, str(x[0]))):
        out.append({
            "code": code,
            "label": _status_label(code, labels) if code else "—",
            "count": count,
        })
    return out


def _empty_report(today: date, warehouse_id: int | None, expiring_days: int) -> dict:
    return {
        "generated_at": today.isoformat(),
        "warehouse_id": warehouse_id,
        "expiring_days": expiring_days,
        "status_filter": "all",
        "summary": {
            "contracts_total": 0,
            "amendments_total": 0,
            "expiring_soon": 0,
            "auto_renew": 0,
            "by_contract_status": [],
            "by_amendment_status": [],
        },
        "clients": [],
        "warehouses": [],
    }
