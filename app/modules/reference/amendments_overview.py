"""Обзор ДС по складам для экрана справочников."""
from __future__ import annotations

from datetime import date, timedelta

from app.db import db
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    TariffRule,
    UnitOfMeasure,
    Warehouse,
)


def _lifecycle_status(amd: dict, today: date) -> str:
    eff_to = amd.get("effective_to")
    if amd.get("status") in ("expired", "terminated", "completed"):
        return "completed"
    if eff_to and eff_to < today:
        return "completed"
    if amd.get("status") == "active":
        return "active"
    return amd.get("status") or "draft"


def _expiring_soon(d: date | None, today: date, days: int = 30) -> bool:
    if not d:
        return False
    return today <= d <= today + timedelta(days=days)


def _warehouse_filter(user: dict):
    if user.get("is_admin"):
        return True
    wh_ids = user.get("warehouse_ids") or []
    return Warehouse.id.in_(wh_ids) if wh_ids else False


def amendments_overview(user: dict) -> list[dict]:
    wh_filter = _warehouse_filter(user)
    if wh_filter is not True and wh_filter is False:
        return []

    q = (
        db.session.query(
            Warehouse,
            Client,
            Contract,
            ProductType,
            ContractAmendment,
            TariffRule,
            UnitOfMeasure,
        )
        .join(Contract, Contract.warehouse_id == Warehouse.id)
        .join(Client, Client.id == Contract.client_id)
        .join(ProductType, ProductType.id == Contract.product_type_id)
        .join(ContractAmendment, ContractAmendment.contract_id == Contract.id)
        .outerjoin(TariffRule, TariffRule.amendment_id == ContractAmendment.id)
        .outerjoin(UnitOfMeasure, UnitOfMeasure.id == TariffRule.unit_id)
        .filter(Contract.status.in_(("active", "draft")))
    )
    if wh_filter is not True:
        q = q.filter(wh_filter)
    q = q.order_by(
        Warehouse.name,
        Client.name,
        ContractAmendment.effective_from.desc(),
        TariffRule.sort_order,
        TariffRule.id,
    )

    today = date.today()
    warehouses: dict[int, dict] = {}

    for wh, client, contract, pt, am, tr, unit in q.all():
        wid = wh.id
        warehouses.setdefault(wid, {
            "warehouse_id": wid,
            "warehouse_code": wh.code,
            "warehouse_name": wh.name,
            "clients": {},
        })
        wh_node = warehouses[wid]
        cid = client.id
        wh_node["clients"].setdefault(cid, {
            "client_id": cid,
            "client_name": client.name,
            "contract_id": contract.id,
            "contract_number": contract.number,
            "service_name": pt.name if pt else None,
            "amendments": {},
        })
        client_node = wh_node["clients"][cid]
        aid = am.id
        if aid not in client_node["amendments"]:
            client_node["amendments"][aid] = {
                "id": aid,
                "number": am.number,
                "status": am.status,
                "auto_renew": False,
                "effective_from": am.effective_from.isoformat() if am.effective_from else None,
                "effective_to": am.effective_to.isoformat() if am.effective_to else None,
                "signed_date": None,
                "source_document": am.source_file_path,
                "lifecycle": _lifecycle_status({
                    "status": am.status,
                    "effective_to": am.effective_to,
                }, today),
                "expiring_soon": _expiring_soon(am.effective_to, today),
                "tariffs": [],
            }

        if tr and tr.id:
            ex = float(tr.rate_ex_vat) if tr.rate_ex_vat is not None else None
            inc = round(ex * 1.22, 2) if ex is not None else None
            if ex is not None:
                ex = round(ex, 2)
            client_node["amendments"][aid]["tariffs"].append({
                "id": tr.id,
                "name": tr.name,
                "billing_line_code": tr.billing_line_code,
                "rate_ex_vat": ex,
                "rate_inc_vat": inc,
                "unit_code": unit.code if unit else None,
                "valid_from": tr.valid_from.isoformat() if tr.valid_from else None,
                "valid_to": tr.valid_to.isoformat() if tr.valid_to else None,
                "inventory_tracked": tr.report_role == "inventory_management",
                "report_role": tr.report_role,
                "report_scope": tr.report_scope or "period",
                "quantity_source": tr.quantity_source,
                "is_custom": bool(tr.is_custom),
                "price_agreed": bool(tr.price_agreed),
                "optional_agreed": not bool(tr.price_agreed),
                "sort_order": tr.sort_order or 0,
                "expiring_soon": _expiring_soon(tr.valid_to, today),
            })

    result = []
    for wh in sorted(warehouses.values(), key=lambda x: x["warehouse_name"]):
        clients = []
        for cl in sorted(wh["clients"].values(), key=lambda x: x["client_name"]):
            amds = sorted(
                cl["amendments"].values(),
                key=lambda a: (0 if a["lifecycle"] == "active" else 1, a["effective_from"] or ""),
                reverse=True,
            )
            cl["amendments"] = amds
            clients.append(cl)
        wh["clients"] = clients
        result.append(wh)
    return result
