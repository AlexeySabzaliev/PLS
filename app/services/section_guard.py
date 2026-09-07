"""Заглушки разделов/ролей на весь портал.

Механизм «техработ»: админ ставит/снимает заглушку на конкретный раздел
(или роль). Для не-админов такой раздел отдаёт страницу/JSON-заглушку (503),
при этом остальной портал продолжает работать — блокируется только затронутая
часть.

Это НЕ «страницы в разработке» (их делает app.web.stub_routes), а аварийный
переключатель на время работ/багфиксов.
"""
from __future__ import annotations

from urllib.parse import parse_qs

from app.modules.reference.models import Role

# Портал модульный: УСС, УЗнТ + общие справочники. Заглушки работают на все модули.

PORTAL_MODULES: list[dict] = [
    {"module": "uss", "label": "УСС"},
    {"module": "uznt", "label": "УЗнТ"},
    {"module": "reference", "label": "Справочники"},
]

# Все разделы портала (для админ-панели заглушек).
PORTAL_SECTIONS: list[dict] = [
    # УСС
    {"module": "uss", "key": "uss_home", "label": "УСС — обзор", "path": "/uss/"},
    {"module": "uss", "key": "uss_ops_transport", "label": "УСС — транспортная логистика", "path": "/uss/transport"},
    {"module": "uss", "key": "uss_ops_warehouse", "label": "УСС — складская логистика", "path": "/uss/warehouse"},
    {"module": "uss", "key": "uss_ops_inventory", "label": "УСС — управление запасами", "path": "/uss/inventory"},
    {"module": "uss", "key": "uss_billing", "label": "УСС — биллинг", "path": "/uss/billing"},
    {"module": "uss", "key": "uss_reports", "label": "УСС — отчёты", "path": "/uss/reports"},
    {"module": "uss", "key": "uss_process_lines", "label": "УСС — линии процессов", "path": "/uss/"},
    {"module": "uss", "key": "uss_admin", "label": "УСС — администрирование", "path": "/admin/reference"},
    # УЗнТ
    {"module": "uznt", "key": "uznt_home", "label": "УЗнТ — обзор", "path": "/uznt/"},
    {"module": "uznt", "key": "requests_transport", "label": "УЗнТ — заявки на перевозку", "path": "/uznt/requests"},
    {"module": "uznt", "key": "tenders", "label": "УЗнТ — тендеры", "path": "/uznt/tenders"},
    {"module": "uznt", "key": "request_analytics", "label": "УЗнТ — аналитика заявок", "path": "/uznt/analytics"},
    # Справочники
    {"module": "reference", "key": "ref_clients", "label": "Справочники — клиенты", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_contracts", "label": "Справочники — договоры", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_amendments", "label": "Справочники — доп. соглашения", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_locations", "label": "Справочники — склады/площадки", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_units", "label": "Справочники — единицы измерения", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_tariff_codes", "label": "Справочники — тарифные ставки", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_staff", "label": "Справочники — персонал/ФОТ", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_vehicle_types", "label": "Справочники — типы ТС", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_roles", "label": "Справочники — роли", "path": "/admin/reference"},
    {"module": "reference", "key": "ref_permissions", "label": "Справочники — доступ (админ)", "path": "/admin/reference"},
]

TOP_SECTION_KEYS = frozenset(s["key"] for s in PORTAL_SECTIONS)
# Соответствие справочника (catalog) → раздел ref_*.
REF_CATALOG_SECTION: dict[str, str] = {
    "clients": "ref_clients",
    "contracts": "ref_contracts",
    "amendments": "ref_amendments",
    "warehouses": "ref_locations",
    "units": "ref_units",
    "tariff_rules": "ref_tariff_codes",
    "staff": "ref_staff",
    "warehouse-staff": "ref_staff",
    "vehicle_types": "ref_vehicle_types",
    "roles": "ref_roles",
    "user_access": "ref_permissions",
}

# (путь, раздел) — точные/префиксные соответствия для page и API.
_PATH_SECTIONS: list[tuple[str, str]] = [
    ("/uss/", "uss_home"),
    ("/uss/transport", "uss_ops_transport"),
    ("/uss/warehouse", "uss_ops_warehouse"),
    ("/uss/inventory", "uss_ops_inventory"),
    ("/uss/billing", "uss_billing"),
    ("/uss/reports", "uss_reports"),
    ("/api/billing", "uss_billing"),
    ("/api/uss/transport", "uss_ops_transport"),
    ("/api/uss/warehouse", "uss_ops_warehouse"),
    ("/api/uss/inventory", "uss_ops_inventory"),
    ("/api/process", "uss_process_lines"),
    ("/api/uznt", "requests_transport"),
    ("/uznt/requests", "requests_transport"),
    ("/uznt/tenders", "tenders"),
    ("/uznt/analytics", "request_analytics"),
    ("/uznt/", "uznt_home"),
]

# Входные точки портала — блокируются при заглушке на роль пользователя.
ROLE_ENTRY_PATHS = ("/", "/uss/", "/uznt/")


def _cq(root: str, path: str, query: bytes) -> set[str]:
    """Разделы для пути page/api справочников."""
    secs: set[str] = set()
    for prefix, section in _PATH_SECTIONS:
        if path == prefix or path.startswith(prefix + "/"):
            secs.add(section)
    if root == "web" and path.startswith("/admin/reference"):
        qs = parse_qs(query.decode("utf-8", "ignore"))
        catalog = (qs.get("catalog") or [""])[0]
        if catalog and catalog in REF_CATALOG_SECTION:
            secs.add(REF_CATALOG_SECTION[catalog])
        else:
            secs.add("ref_clients")
    if root == "api" and path.startswith("/api/reference"):
        parts = path.split("/")
        # /api/reference/<catalog>[[/<int:id>]]
        if len(parts) >= 3:
            candidate = parts[3] if parts[3] else ""
            if candidate == "warehouse-staff":
                secs.add("ref_staff")
            elif candidate in REF_CATALOG_SECTION:
                secs.add(REF_CATALOG_SECTION[candidate])
            elif candidate == "amendments-overview":
                secs.add("ref_amendments")
            elif candidate and candidate not in {"meta", "lookups"} and len(parts) == 4:
                secs.add("ref_clients")
    return secs


def resolve_section_keys(path: str, query: bytes = b"") -> set[str]:
    """Разделы, соответствующие запросу (без учёта ролей пользователя)."""
    root = "api" if path.startswith("/api/") else "web"
    return _cq(root, path, query)


def active_blocker(
    user: dict | None,
    path: str,
    query: bytes = b"",
    maintenance: dict | None = None,
) -> tuple[str, str, str] | None:
    """Признак блокировки запроса заглушкой.

    Возвращает (target_type, target_key, message) или None (не блокирован).
    """
    if not user or user.get("is_admin"):
        return None
    from app.services.maintenance import maintenance_for_user

    data = maintenance or maintenance_for_user(user)

    # Роль под заглушкой — блокируются входные точки портала этой роли.
    user_roles = set(user.get("role_codes") or [])
    for role, message in (data.get("roles") or {}).items():
        if role in user_roles and (path == "/" or path.startswith("/uss") or path.startswith("/uznt")):
            return ("role", role, message)

    sections = data.get("sections") or {}
    if not sections:
        return None
    for key in resolve_section_keys(path, query):
        message = sections.get(key)
        if message:
            return ("section", key, message)
    return None


def portal_catalog() -> dict:
    """Реестр разделов/модулей/ролей для админ-панели заглушек."""
    roles = [{"code": r.code, "name": r.name} for r in Role.query.order_by(Role.code).all()]
    return {
        "modules": PORTAL_MODULES,
        "sections": PORTAL_SECTIONS,
        "roles": roles,
    }