"""CRUD API справочников."""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

from flask import Blueprint, current_app, g, request
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.core.auth import login_required
from app.core.permissions import user_has_reference_section
from app.db import db
from app.modules.reference.client_names import canonical_client_name, find_duplicate_client_name
from app.modules.reference.amendment_apply import apply_parsed_to_amendment
from app.modules.reference.amendment_docx_import import parse_amendment_docx, parsed_to_dict
from app.modules.reference.amendments_overview import amendments_overview as build_amendments_overview
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Role,
    StaffPosition,
    TariffRule,
    UnitOfMeasure,
    VehicleType,
    Warehouse,
)
from app.modules.uss.services.staff_positions import (
    create_staff_position,
    deactivate_staff_position,
    list_position_versions,
    list_staff_positions,
    update_staff_position,
)
from app.modules.uss.services.tariff_codes import infer_billing_line_code, is_placeholder_code
from app.modules.uss.services.tariff_quantity import apply_tariff_defaults, billing_line_code_choices

bp = Blueprint("reference_api", __name__, url_prefix="/api/reference")

CATALOGS: dict[str, tuple[type, list[str]]] = {
    # security_name не в UI: сопоставление с security.bsh-ru.ru идёт по name (частичное).
    "clients": (Client, ["id", "name", "is_active"]),
    "warehouses": (
        Warehouse,
        ["id", "code", "name", "work_day_start", "work_day_end", "security_visit_place", "is_active"],
    ),
    "product_types": (ProductType, ["id", "code", "name", "is_active"]),
    "contracts": (Contract, ["id", "client_id", "warehouse_id", "product_type_id", "number", "status"]),
    "amendments": (
        ContractAmendment,
        ["id", "contract_id", "number", "status", "effective_from", "effective_to", "source_file_path"],
    ),
    "units": (UnitOfMeasure, ["id", "code", "name", "is_active"]),
    "tariff_rules": (TariffRule, [
        "id", "contract_id", "amendment_id", "billing_line_code", "name",
        "unit_id", "report_role", "report_scope", "quantity_source",
        "rate_line_code", "quantity_divisor",
        "is_custom", "price_agreed", "sort_order", "valid_from", "valid_to",
        "rate_ex_vat",
    ]),
    "staff": (StaffPosition, ["id", "code", "name", "is_active"]),
    "vehicle_types": (VehicleType, ["id", "code", "name", "sort_order", "dimensions_label"]),
    "roles": (Role, ["id", "code", "name"]),
}

READ_ONLY_CATALOGS = frozenset({"roles"})
HIDDEN_CATALOGS = frozenset({"staff", "roles"})

SECTION_MAP = {
    "clients": "ref_clients",
    "contracts": "ref_contracts",
    "amendments": "ref_amendments",
    "warehouses": "ref_locations",
    "product_types": "ref_clients",
    "units": "ref_units",
    "tariff_rules": "ref_tariff_codes",
    "staff": "ref_staff",
    "warehouse_staff": "ref_staff",
    "vehicle_types": "ref_vehicle_types",
    "roles": "ref_roles",
}

DATE_FIELDS = frozenset({"effective_from", "effective_to", "valid_from", "valid_to"})
TIME_FIELDS = frozenset({"work_day_start", "work_day_end"})
BOOL_FIELDS = frozenset({"is_active", "is_custom", "price_agreed"})
INT_FIELDS = frozenset({
    "client_id", "warehouse_id", "product_type_id", "contract_id",
    "amendment_id", "unit_id", "sort_order", "vehicle_type_id",
})
DECIMAL_FIELDS = frozenset({"rate_ex_vat", "quantity_divisor"})

# Поля только для чтения в UI (технические)
READONLY_UI_FIELDS = frozenset({
    "id", "source_file_path", "rate_line_code",
})

# Скрытые в таблице (доступны в расширенном режиме)
ADVANCED_UI_FIELDS = frozenset({
    "billing_line_code", "rate_line_code", "quantity_divisor", "sort_order",
    "report_scope", "price_agreed",
})

LOOKUP_FIELDS = {
    "client_id": "clients",
    "warehouse_id": "warehouses",
    "product_type_id": "product_types",
    "contract_id": "contracts",
    "amendment_id": "amendments",
    "unit_id": "units",
}

FIELD_LABELS = {
    "id": "№",
    "name": "Наименование",
    "code": "Код",
    "security_visit_place": "Место визита СБ",
    "work_day_start": "Начало смены",
    "work_day_end": "Окончание смены",
    "is_active": "Активен",
    "client_id": "Клиент",
    "warehouse_id": "Склад",
    "product_type_id": "Тип продукта",
    "number": "Номер",
    "status": "Статус",
    "contract_id": "Договор",
    "effective_from": "Действует с",
    "effective_to": "Действует до",
    "source_file_path": "Файл ДС",
    "billing_line_code": "Код строки (тех.)",
    "amendment_id": "Доп. соглашение",
    "unit_id": "Ед. изм.",
    "report_role": "Кто вводит",
    "report_scope": "Где вводится",
    "quantity_source": "Как считается",
    "is_custom": "Доп. ставка",
    "price_agreed": "Цена согласована",
    "sort_order": "Порядок",
    "valid_from": "Ставка с",
    "valid_to": "Ставка до",
    "rate_ex_vat": "Тариф без НДС",
    "rate_line_code": "Код ставки (тех.)",
    "quantity_divisor": "Делитель",
    "dimensions_label": "Габариты, м",
}

CATALOG_LABELS = {
    "clients": "Клиенты",
    "warehouses": "Склады",
    "product_types": "Типы продукта",
    "contracts": "Договоры",
    "amendments": "Доп. соглашения",
    "units": "Единицы измерения",
    "tariff_rules": "Ставки",
    "staff": "Должности",
    "warehouse_staff": "Штат ФОТ",
    "vehicle_types": "Типы ТС",
    "roles": "Роли",
}

# Подписи полей, зависящие от справочника (number — и у договора, и у ДС)
CATALOG_FIELD_LABELS: dict[str, dict[str, str]] = {
    "amendments": {
        "contract_id": "Договор (осн.)",
        "number": "№ ДС",
    },
    "contracts": {
        "number": "№ договора",
    },
    "tariff_rules": {
        "amendment_id": "ДС",
        "contract_id": "Договор (осн.)",
    },
}

CATALOG_HINTS = {
    "warehouses": (
        "График смены (начало/окончание) задаёт автоматический расчёт сверхурочных ТС "
        "по времени убытия. «Место визита СБ» — фильтр портала охраны."
    ),
    "product_types": "Неиспользуемые типы можно деактивировать — они не появятся при создании договора.",
    "units": "Неактивные единицы скрыты в новых ставках. «машина» и «м²·день» оставлены в БД для алгоритмов.",
    "vehicle_types": "Для колонки «Тип ТС» в транспортной смене. Габариты: 13,6×2,45×2,70 (д×ш×в, м). Госномера вводятся вручную в смене.",
    "amendments": "Доп. соглашения (ДС) к договору. Загрузите файл Word — система создаст черновик ДС со ставками из таблицы.",
    "tariff_rules": "Основные ставки из ДС, дополнительные — согласованы отдельно (флаг «Доп. ставка»).",
    "warehouse_staff": (
        "Должности, оклад (₽/мес без НДС) и численность по складу. "
        "При изменении оклада или численности укажите дату «Действует с» — "
        "создаётся новая версия для отчёта «ФОТ vs операционка»."
    ),
}

STATUS_CHOICES = {
    "contracts": [("active", "Действует"), ("suspended", "Приостановлен"), ("closed", "Закрыт")],
    "amendments": [
        ("draft", "Черновик"),
        ("active", "Действует"),
        ("superseded", "Заменено"),
    ],
}

REPORT_ROLE_CHOICES = [
    ("", "— система / авто"),
    ("transport_logistics", "Транспортная логистика"),
    ("warehouse_logistics", "Складская логистика"),
    ("inventory_management", "Управление запасами"),
]

QUANTITY_SOURCE_CHOICES = [
    ("", "— по умолчанию"),
    ("auto_contract_param", "Система: параметр договора"),
    ("auto_vehicle", "Система: из транспорта"),
    ("manual_vehicle", "Ручной ввод в строке ТС"),
    ("manual_daily", "Ручной ввод: суточные допы"),
    ("manual_inventory", "Ручной ввод: упр. запасами"),
    ("none", "Не вводится"),
]

REPORT_SCOPE_CHOICES = [
    ("", "—"),
    ("vehicle", "На строке ТС"),
    ("period", "Итог под таблицей"),
]


def _validate_client_name(name: str, *, exclude_id: int | None = None) -> tuple[str, tuple[dict, int] | None]:
    cleaned = canonical_client_name((name or "").strip())
    if not cleaned:
        return cleaned, ({"error": "validation", "message": "Укажите наименование клиента"}, 422)
    dup = find_duplicate_client_name(cleaned, exclude_id=exclude_id)
    if dup:
        return cleaned, ({
            "error": "duplicate_client",
            "message": f"Клиент с таким именем уже есть: «{dup}»",
        }, 422)
    return cleaned, None


def _format_time_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if len(text) >= 5 and text[2] == ":":
        return text[:5]
    return text or None


def _parse_time_field(value) -> time | None:
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    if len(text) >= 5 and text[2] == ":":
        parts = text[:5].split(":")
        return time(int(parts[0]), int(parts[1]))
    return None


def _serialize(model, fields: list[str]) -> dict:
    out = {}
    for f in fields:
        val = getattr(model, f)
        if isinstance(val, date):
            out[f] = val.isoformat()
        elif isinstance(val, time):
            out[f] = val.strftime("%H:%M")
        elif val is not None and f in DECIMAL_FIELDS:
            out[f] = float(val)
        else:
            out[f] = val
    return out


def _coerce_field(name: str, value):
    if value is None or value == "":
        return None
    if name in BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")
    if name in INT_FIELDS:
        return int(value)
    if name in DECIMAL_FIELDS:
        return float(value)
    if name in DATE_FIELDS:
        return date.fromisoformat(str(value)[:10])
    if name in TIME_FIELDS:
        parsed = _parse_time_field(value)
        if parsed is None:
            raise ValueError(f"Некорректное время для {name}")
        return parsed
    return value


def _apply_payload(model, data: dict, fields: list[str], *, for_create: bool) -> None:
    skip = {"id"} if for_create else {"id"}
    for key, value in data.items():
        if key in skip or key not in fields:
            continue
        # Технические поля (billing_line_code) задаются при создании, но не редактируются в UI.
        if not for_create and key in READONLY_UI_FIELDS and key != "id":
            continue
        setattr(model, key, _coerce_field(key, value))


def _tariff_billing_line_slug(name: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in name.lower())[:40]
    return slug or "line"


def _normalize_tariff_row(row: TariffRule) -> None:
    """Согласовать код строки, роль и quantity_source по реестру (без упрощения каталога)."""
    code = (row.billing_line_code or "").strip()
    name = (row.name or "").strip()
    if is_placeholder_code(code):
        inferred = infer_billing_line_code(name, None)
        if inferred and inferred != code:
            row.billing_line_code = inferred
            code = inferred
    elif code.startswith("custom_") and not row.is_custom:
        inferred = infer_billing_line_code(name, None)
        if inferred and inferred != code:
            row.billing_line_code = inferred
            code = inferred
    normalized = apply_tariff_defaults({
        "billing_line_code": code,
        "name": name,
        "report_role": row.report_role,
        "report_scope": row.report_scope,
        "quantity_source": row.quantity_source,
        "is_custom": row.is_custom,
    })
    row.report_role = normalized.get("report_role")
    row.report_scope = normalized.get("report_scope")
    row.quantity_source = normalized.get("quantity_source")


def _prepare_tariff_create(data: dict) -> tuple[dict, tuple[dict, int] | None]:
    """Нормализация и проверка полей новой ставки. Возвращает (data, error_response)."""
    amendment_id = data.get("amendment_id")
    if not amendment_id:
        return data, (
            {"error": "amendment_required", "message": "Ставка может быть создана только в рамках ДС"},
            400,
        )
    amendment = db.session.get(ContractAmendment, int(amendment_id))
    if not amendment:
        return data, (
            {"error": "amendment_not_found", "message": "Доп. соглашение не найдено"},
            404,
        )
    if not data.get("contract_id"):
        data = {**data, "contract_id": amendment.contract_id}
    if not data.get("billing_line_code"):
        name = str(data.get("name") or "line").strip() or "line"
        data = {**data, "billing_line_code": f"custom_{_tariff_billing_line_slug(name)}"}
    name = str(data.get("name") or "").strip()
    if name:
        code = str(data.get("billing_line_code") or "").strip()
        is_custom = bool(data.get("is_custom"))
        if is_placeholder_code(code) or (code.startswith("custom_") and not is_custom):
            inferred = infer_billing_line_code(name, None)
            if inferred:
                data = {**data, "billing_line_code": inferred}
        elif not code:
            data = {**data, "billing_line_code": f"custom_{_tariff_billing_line_slug(name)}"}
    name = str(data.get("name") or "").strip()
    if not name:
        return data, (
            {"error": "validation", "message": "Укажите наименование ставки"},
            422,
        )
    if not data.get("valid_from"):
        return data, (
            {"error": "validation", "message": "Укажите дату начала действия ставки"},
            422,
        )
    return data, None


def _check_ref_access(catalog: str) -> bool:
    section = SECTION_MAP.get(catalog, "ref_clients")
    return user_has_reference_section(g.user, section)


def _get_catalog(catalog: str):
    if catalog not in CATALOGS:
        return None, None
    return CATALOGS[catalog]


def _lookup_clients(*, active_only: bool = False) -> list[dict]:
    q = Client.query.order_by(Client.name)
    if active_only:
        q = q.filter_by(is_active=True)
    return [{"id": r.id, "label": r.name} for r in q.all()]


def _lookup_warehouses(*, active_only: bool = False) -> list[dict]:
    q = Warehouse.query.order_by(Warehouse.name)
    if active_only:
        q = q.filter_by(is_active=True)
    return [{"id": r.id, "label": f"{r.name} ({r.code})"} for r in q.all()]


def _lookup_product_types(*, active_only: bool = False) -> list[dict]:
    q = ProductType.query.order_by(ProductType.name)
    if active_only:
        q = q.filter_by(is_active=True)
    return [{"id": r.id, "label": r.name, "code": r.code, "is_active": r.is_active} for r in q.all()]


def _lookup_units(*, active_only: bool = False) -> list[dict]:
    q = UnitOfMeasure.query.order_by(UnitOfMeasure.name)
    if active_only:
        q = q.filter_by(is_active=True)
    return [{"id": r.id, "label": f"{r.name} ({r.code})", "code": r.code} for r in q.all()]


def _lookup_contracts() -> list[dict]:
    rows = (
        Contract.query.join(Client).join(Warehouse)
        .order_by(Client.name, Contract.number)
        .all()
    )
    out = []
    for r in rows:
        client = r.client.name if r.client else "?"
        wh = r.warehouse.name if r.warehouse else "?"
        out.append({
            "id": r.id,
            "label": f"{r.number} — {client}, {wh}",
            "client_id": r.client_id,
            "client_name": client,
        })
    return out


def _lookup_amendments() -> list[dict]:
    rows = ContractAmendment.query.order_by(ContractAmendment.contract_id, ContractAmendment.number).all()
    return [
        {
            "id": r.id,
            "label": f"ДС №{r.number}",
            "number": r.number,
            "contract_id": r.contract_id,
            "effective_from": r.effective_from.isoformat() if r.effective_from else None,
            "effective_to": r.effective_to.isoformat() if r.effective_to else None,
            "status": r.status,
        }
        for r in rows
    ]


def _build_lookups(*, active_only: bool = True) -> dict:
    return {
        "clients": _lookup_clients(active_only=active_only),
        "warehouses": _lookup_warehouses(active_only=active_only),
        "product_types": _lookup_product_types(active_only=active_only),
        "contracts": _lookup_contracts(),
        "amendments": _lookup_amendments(),
        "units": _lookup_units(active_only=active_only),
    }


def _field_label(catalog: str, field: str) -> str:
    return CATALOG_FIELD_LABELS.get(catalog, {}).get(field) or FIELD_LABELS.get(field, field)


def _field_meta_for_catalog(catalog: str, fields: list[str]) -> list[dict]:
    meta = []
    for f in fields:
        if f == "id":
            continue
        entry = {
            "field": f,
            "label": _field_label(catalog, f),
            "lookup": LOOKUP_FIELDS.get(f),
            "readonly": f in READONLY_UI_FIELDS or (
                catalog == "product_types" and f in ("code", "name")
            ),
            "advanced": f in ADVANCED_UI_FIELDS,
            "type": "bool" if f in BOOL_FIELDS else (
                "date" if f in DATE_FIELDS else (
                    "time" if f in TIME_FIELDS else (
                        "select" if f == "status" and catalog in STATUS_CHOICES else (
                            "select" if f == "billing_line_code" and catalog == "tariff_rules" else (
                                "select" if f == "report_role" else (
                                    "select" if f == "quantity_source" else (
                                        "select" if f == "report_scope" else "text"
                                    )
                                )
                            )
                        )
                    )
                )
            ),
        }
        if f == "status" and catalog in STATUS_CHOICES:
            entry["choices"] = [{"value": v, "label": l} for v, l in STATUS_CHOICES[catalog]]
        if f == "report_role":
            entry["choices"] = [{"value": v, "label": l} for v, l in REPORT_ROLE_CHOICES]
        if f == "quantity_source":
            entry["choices"] = [{"value": v, "label": l} for v, l in QUANTITY_SOURCE_CHOICES]
        if f == "report_scope":
            entry["choices"] = [{"value": v, "label": l} for v, l in REPORT_SCOPE_CHOICES]
        if f == "billing_line_code" and catalog == "tariff_rules":
            entry["choices"] = billing_line_code_choices()
        meta.append(entry)
    return meta


@bp.get("/lookups")
@login_required
def reference_lookups():
    active_only = request.args.get("all") != "1"
    return _build_lookups(active_only=active_only)


@bp.get("/meta")
@login_required
def catalog_meta():
    items = []
    for code, (_, fields) in CATALOGS.items():
        if code in HIDDEN_CATALOGS:
            continue
        if not _check_ref_access(code):
            continue
        items.append({
            "code": code,
            "label": CATALOG_LABELS.get(code, code),
            "hint": CATALOG_HINTS.get(code, ""),
            "fields": fields,
            "field_meta": _field_meta_for_catalog(code, fields),
            "read_only": code in READ_ONLY_CATALOGS,
            "section": SECTION_MAP.get(code),
            "grouped": code == "tariff_rules",
            "supports_upload": code == "amendments",
        })
    if _check_ref_access("warehouse_staff"):
        items.append({
            "code": "warehouse_staff",
            "label": CATALOG_LABELS["warehouse_staff"],
            "hint": CATALOG_HINTS.get("warehouse_staff", ""),
            "fields": ["warehouse_id", "name", "monthly_rate", "headcount", "sort_order"],
            "field_meta": [],
            "read_only": False,
            "section": SECTION_MAP.get("warehouse_staff"),
            "grouped": False,
            "custom_ui": True,
        })
    return {
        "catalogs": items,
        "field_labels": FIELD_LABELS,
        "lookups": _build_lookups(active_only=False),
    }


RESERVED_CATALOGS = frozenset({"meta", "lookups"})


@bp.delete("/tariff_rules/bulk")
@login_required
def bulk_delete_tariff_rules():
    """Массовое удаление ставок по ДС, договору (без ДС) или клиенту."""
    if not _check_ref_access("tariff_rules"):
        return {"error": "forbidden"}, 403
    amendment_id = request.args.get("amendment_id", type=int)
    client_id = request.args.get("client_id", type=int)
    contract_id = request.args.get("contract_id", type=int)
    unlinked = request.args.get("unlinked") == "1"
    if amendment_id:
        deleted = TariffRule.query.filter_by(amendment_id=amendment_id).delete(synchronize_session=False)
    elif contract_id and unlinked:
        valid_ids = {
            a.id for a in ContractAmendment.query.filter_by(contract_id=contract_id).all()
        }
        q = TariffRule.query.filter_by(contract_id=contract_id)
        if valid_ids:
            q = q.filter(
                db.or_(
                    TariffRule.amendment_id.is_(None),
                    ~TariffRule.amendment_id.in_(valid_ids),
                )
            )
        deleted = q.delete(synchronize_session=False)
    elif client_id:
        contract_ids = [c.id for c in Contract.query.filter_by(client_id=client_id).all()]
        if not contract_ids:
            deleted = 0
        else:
            deleted = TariffRule.query.filter(
                TariffRule.contract_id.in_(contract_ids),
            ).delete(synchronize_session=False)
    else:
        return {"error": "amendment_id_client_id_or_contract_unlinked_required"}, 400
    db.session.commit()
    return {
        "deleted": deleted,
        "amendment_id": amendment_id,
        "client_id": client_id,
        "contract_id": contract_id,
        "unlinked": unlinked if contract_id else None,
    }


@bp.get("/amendments-overview")
@login_required
def amendments_overview_api():
    if not _check_ref_access("amendments"):
        return {"error": "forbidden"}, 403
    return build_amendments_overview(g.user)


@bp.get("/<catalog>")
@login_required
def list_catalog(catalog: str):
    if catalog in RESERVED_CATALOGS:
        if catalog == "lookups":
            return reference_lookups()
        if catalog == "meta":
            return catalog_meta()
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = spec
    if catalog == "vehicle_types":
        rows = model.query.order_by(VehicleType.sort_order, VehicleType.id).limit(500).all()
    elif catalog == "tariff_rules":
        rows = model.query.order_by(
            TariffRule.contract_id, TariffRule.is_custom, TariffRule.sort_order, TariffRule.id,
        ).limit(2000).all()
    else:
        rows = model.query.order_by(model.id).limit(500).all()
    return {"items": [_serialize(r, fields) for r in rows]}


@bp.post("/<catalog>")
@login_required
def create_catalog_item(catalog: str):
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if catalog in READ_ONLY_CATALOGS:
        return {"error": "read_only"}, 400
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = spec
    data = request.get_json(silent=True) or {}
    if catalog == "clients":
        cleaned, err = _validate_client_name(data.get("name", ""))
        if err:
            body, status = err
            return body, status
        data = {**data, "name": cleaned}
    if catalog == "tariff_rules":
        data, err = _prepare_tariff_create(data)
        if err:
            body, status = err
            return body, status
    row = model()
    _apply_payload(row, data, fields, for_create=True)
    if catalog == "tariff_rules":
        _normalize_tariff_row(row)
    if catalog == "amendments" and not getattr(row, "status", None):
        row.status = "draft"
    if catalog == "tariff_rules" and not getattr(row, "billing_line_code", None):
        return {
            "error": "validation",
            "message": "Не указан код строки тарифа (billing_line_code)",
        }, 422
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {
            "error": "db_constraint",
            "message": "Не удалось сохранить ставку: проверьте уникальность кода строки и связь с ДС",
        }, 422
    return _serialize(row, fields), 201


@bp.put("/<catalog>/<int:item_id>")
@login_required
def update_catalog_item(catalog: str, item_id: int):
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if catalog in READ_ONLY_CATALOGS:
        return {"error": "read_only"}, 400
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, fields = spec
    row = db.session.get(model, item_id)
    if not row:
        return {"error": "not_found"}, 404
    data = request.get_json(silent=True) or {}
    if catalog == "clients" and "name" in data:
        cleaned, err = _validate_client_name(data.get("name", ""), exclude_id=item_id)
        if err:
            body, status = err
            return body, status
        data = {**data, "name": cleaned}
    # Типы продукта: только is_active
    if catalog == "product_types":
        if "is_active" in data:
            row.is_active = _coerce_field("is_active", data["is_active"])
    else:
        _apply_payload(row, data, fields, for_create=False)
    if catalog == "tariff_rules":
        _normalize_tariff_row(row)
    db.session.commit()
    return _serialize(row, fields)


@bp.delete("/<catalog>/<int:item_id>")
@login_required
def delete_catalog_item(catalog: str, item_id: int):
    """Hard delete строки справочника. При FK-ошибке запись остаётся — используйте db-vacuum."""
    spec = _get_catalog(catalog)
    if not spec[0]:
        return {"error": "not_found"}, 404
    if catalog in READ_ONLY_CATALOGS:
        return {"error": "read_only"}, 400
    if not _check_ref_access(catalog):
        return {"error": "forbidden"}, 403
    model, _fields = spec
    row = db.session.get(model, item_id)
    if not row:
        return {"error": "not_found"}, 404
    try:
        db.session.delete(row)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {
            "error": "constraint_violation",
            "message": (
                "Запись связана с другими данными (договоры, ставки, операции). "
                "Сначала удалите зависимости или выполните flask pls db-vacuum --yes."
            ),
        }, 409
    return {"deleted": True, "id": item_id, "mode": "hard_delete"}


@bp.post("/amendments/<int:item_id>/upload")
@login_required
def upload_amendment_doc(item_id: int):
    if not _check_ref_access("amendments"):
        return {"error": "forbidden"}, 403
    row = db.session.get(ContractAmendment, item_id)
    if not row:
        return {"error": "not_found"}, 404
    file = request.files.get("file")
    if not file or not file.filename:
        return {"error": "no_file"}, 400
    ext = Path(file.filename).suffix.lower()
    if ext not in (".docx", ".doc"):
        return {"error": "invalid_format", "message": "Нужен файл Word (.docx)"}, 400
    if ext == ".doc":
        return {"error": "invalid_format", "message": "Сохраните документ как .docx"}, 400

    upload_dir = Path(current_app.instance_path) / "uploads" / "amendments"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe = secure_filename(file.filename) or "amendment.docx"
    dest = upload_dir / f"{item_id}_{safe}"
    file.save(dest)

    try:
        parsed = parse_amendment_docx(dest.read_bytes(), dest.name)
    except Exception as exc:
        return {
            "error": "parse_failed",
            "message": f"Не удалось разобрать документ Word: {exc}",
        }, 422

    row.source_file_path = str(dest.relative_to(current_app.instance_path))
    row.status = "draft"
    apply_result = apply_parsed_to_amendment(row, parsed)

    db.session.commit()

    fields = CATALOGS["amendments"][1]
    msg = f"Файл загружен. Создано ставок: {apply_result['tariffs_created']}."
    if apply_result["warnings"]:
        msg += " Проверьте номер, даты и ставки в черновике."
    return {
        "amendment": _serialize(row, fields),
        "parsed": parsed_to_dict(parsed),
        "tariffs_created": apply_result["tariffs_created"],
        "warnings": apply_result["warnings"],
        "message": msg,
    }


@bp.post("/amendments/import")
@login_required
def import_amendment_doc():
    """Создать черновик ДС из файла Word."""
    if not _check_ref_access("amendments"):
        return {"error": "forbidden"}, 403
    contract_id = request.form.get("contract_id", type=int)
    if not contract_id:
        return {"error": "contract_id_required"}, 400
    contract = db.session.get(Contract, contract_id)
    if not contract:
        return {"error": "contract_not_found"}, 404
    file = request.files.get("file")
    if not file or not file.filename:
        return {"error": "no_file"}, 400
    ext = Path(file.filename).suffix.lower()
    if ext != ".docx":
        return {"error": "invalid_format", "message": "Нужен файл Word (.docx)"}, 400

    row = ContractAmendment(
        contract_id=contract_id,
        number="черновик",
        status="draft",
        effective_from=date.today(),
    )
    db.session.add(row)
    db.session.flush()

    upload_dir = Path(current_app.instance_path) / "uploads" / "amendments"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe = secure_filename(file.filename) or "amendment.docx"
    dest = upload_dir / f"{row.id}_{safe}"
    file.save(dest)

    try:
        parsed = parse_amendment_docx(dest.read_bytes(), dest.name)
    except Exception as exc:
        db.session.rollback()
        return {
            "error": "parse_failed",
            "message": f"Не удалось разобрать документ Word: {exc}",
        }, 422

    row.source_file_path = str(dest.relative_to(current_app.instance_path))
    apply_result = apply_parsed_to_amendment(row, parsed)
    db.session.commit()

    fields = CATALOGS["amendments"][1]
    n = apply_result["tariffs_created"]
    if n:
        msg = f"Черновик ДС создан. Загружено {n} ставок — проверьте данные и активируйте после корректировки."
    else:
        msg = (
            "Черновик ДС создан, но ставки в документе не найдены. "
            "Проверьте таблицу тарифов в файле или добавьте ставки вручную."
        )
        if apply_result["warnings"]:
            msg += f" ({', '.join(apply_result['warnings'])})"

    return {
        "amendment": _serialize(row, fields),
        "parsed": parsed_to_dict(parsed),
        "tariffs_created": n,
        "warnings": apply_result["warnings"],
        "message": msg,
    }, 201


@bp.get("/warehouse-staff")
@login_required
def warehouse_staff_list():
    if not _check_ref_access("warehouse_staff"):
        return {"error": "forbidden"}, 403
    warehouse_id = request.args.get("warehouse_id", type=int)
    if warehouse_id:
        return {"items": list_staff_positions(warehouse_id)}
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.code).all()
    items = []
    for wh in warehouses:
        items.extend(list_staff_positions(wh.id))
    return {"items": items}


@bp.post("/warehouse-staff")
@login_required
def warehouse_staff_create():
    if not _check_ref_access("warehouse_staff"):
        return {"error": "forbidden"}, 403
    data = request.get_json(silent=True) or {}
    warehouse_id = data.get("warehouse_id")
    if not warehouse_id:
        return {"error": "warehouse_id_required", "message": "Укажите склад"}, 400
    try:
        row = create_staff_position(int(warehouse_id), data)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        return {"error": str(exc), "message": "Проверьте поля позиции"}, 400
    return row, 201


@bp.put("/warehouse-staff/<int:item_id>")
@login_required
def warehouse_staff_update(item_id: int):
    if not _check_ref_access("warehouse_staff"):
        return {"error": "forbidden"}, 403
    data = request.get_json(silent=True) or {}
    try:
        row = update_staff_position(item_id, data)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        if str(exc) == "not_found":
            return {"error": "not_found"}, 404
        return {"error": str(exc), "message": "Проверьте поля позиции"}, 400
    return row


@bp.get("/warehouse-staff/<int:item_id>/versions")
@login_required
def warehouse_staff_versions(item_id: int):
    if not _check_ref_access("warehouse_staff"):
        return {"error": "forbidden"}, 403
    from app.modules.uss.models import WarehouseStaffPosition

    pos = db.session.get(WarehouseStaffPosition, item_id)
    if not pos:
        return {"error": "not_found"}, 404
    return {"items": list_position_versions(item_id)}


@bp.delete("/warehouse-staff/<int:item_id>")
@login_required
def warehouse_staff_delete(item_id: int):
    if not _check_ref_access("warehouse_staff"):
        return {"error": "forbidden"}, 403
    try:
        deactivate_staff_position(item_id)
        db.session.commit()
    except ValueError:
        db.session.rollback()
        return {"error": "not_found"}, 404
    return {"deleted": True, "id": item_id}
