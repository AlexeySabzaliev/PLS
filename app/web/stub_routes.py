"""Страницы-заглушки УЗнТ и незавершённых разделов УСС."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, redirect, render_template, url_for

from app.config import Config
from app.core.auth import get_current_user
from app.core.permissions import (
    user_has_any_request_section,
    user_has_any_uss_section,
    user_has_request_section,
    user_has_uss_section,
)

bp = Blueprint("stub_web", __name__)


def _login_required_page(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("web.index"))
        return view(user, *args, **kwargs)

    return wrapped


def _render_stub(
    user: dict,
    *,
    module: str,
    title: str,
    section: str,
    description: str,
    links: list[dict] | None = None,
):
    return render_template(
        "stub.html",
        user=user,
        app_short=Config.APP_SHORT,
        module=module,
        module_name=Config.MODULE_UZNT_NAME if module == "uznt" else Config.MODULE_USS_NAME,
        title=title,
        section=section,
        description=description,
        links=links or [],
    )


@bp.get("/uznt/")
@_login_required_page
def uznt_index(user):
    if not user_has_any_request_section(user):
        abort(403)
    links = []
    if user_has_request_section(user, "requests_transport") or user_has_request_section(user, "requests_view_all"):
        links.append({"href": "/uznt/requests", "label": "Заявки"})
    if user_has_request_section(user, "tenders"):
        links.append({"href": "/uznt/tenders", "label": "Тендеры"})
    if user_has_request_section(user, "request_analytics"):
        links.append({"href": "/uznt/analytics", "label": "Аналитика"})
    return _render_stub(
        user,
        module="uznt",
        title=Config.MODULE_UZNT_NAME,
        section="uznt_home",
        description="Модуль заявок на транспортировку. Полный UI будет перенесён из Transport.",
        links=links,
    )


@bp.get("/uznt/requests")
@_login_required_page
def uznt_requests(user):
    if not (
        user_has_request_section(user, "requests_transport")
        or user_has_request_section(user, "requests_view_all")
    ):
        abort(403)
    return _render_stub(
        user,
        module="uznt",
        title="Заявки на перевозку",
        section="requests_transport",
        description="Список и обработка заявок GP/материалы — в разработке.",
    )


@bp.get("/uznt/tenders")
@_login_required_page
def uznt_tenders(user):
    if not user_has_request_section(user, "tenders"):
        abort(403)
    return _render_stub(
        user,
        module="uznt",
        title="Тендеры",
        section="tenders",
        description="Тендеры на перевозку — в разработке.",
    )


@bp.get("/uznt/analytics")
@_login_required_page
def uznt_analytics(user):
    if not user_has_request_section(user, "request_analytics"):
        abort(403)
    return _render_stub(
        user,
        module="uznt",
        title="Аналитика заявок",
        section="request_analytics",
        description="Отчёты по заявкам — в разработке.",
    )


@bp.get("/uss/")
@_login_required_page
def uss_index(user):
    if not user_has_any_uss_section(user):
        abort(403)
    links = [
        {"href": "/uss/transport", "label": "Транспортная логистика", "desc": "Ежесменный отчёт: ТС с портала охраны"},
        {"href": "/uss/warehouse", "label": "Складская логистика", "desc": "Ежесменный отчёт: операции склада без привязки к ТС"},
        {"href": "/uss/inventory", "label": "Управление запасами", "desc": "Ежесменный отчёт: площади хранения и доп. работы"},
        {"href": "/uss/billing", "label": "Биллинг", "desc": "Расчёт и выгрузка биллинга ОХ"},
    ]
    if user_has_uss_section(user, "uss_reports"):
        links.append({"href": "/uss/reports", "label": "Отчёты", "desc": "ФОТ, эффективность и аналитика"})
    return render_template(
        "uss/home.html",
        user=user,
        active="home",
        module_name=Config.MODULE_USS_NAME,
        links=links,
    )


