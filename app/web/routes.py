"""Веб-страницы портала."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for

from app.config import Config
from app.core.auth import get_current_user

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        user=get_current_user(),
        app_name=Config.APP_NAME,
        app_short=Config.APP_SHORT,
        module_uznt=Config.MODULE_UZNT_NAME,
        module_uss=Config.MODULE_USS_NAME,
    )


@bp.get("/uss/transport")
def uss_transport():
    return render_template("uss/transport.html", user=get_current_user(), active="transport")


@bp.get("/uss/warehouse")
def uss_warehouse():
    return render_template("uss/warehouse.html", user=get_current_user(), active="warehouse")


@bp.get("/uss/inventory")
def uss_inventory():
    return render_template("uss/inventory.html", user=get_current_user(), active="inventory")


@bp.get("/uss/billing")
def uss_billing():
    return redirect(url_for("web.uss_reports_billing"), code=302)


@bp.get("/uss/reports")
def uss_reports_hub():
    return redirect(url_for("web.uss_reports_billing"), code=302)


@bp.get("/uss/reports/billing")
def uss_reports_billing():
    return render_template(
        "uss/billing.html",
        user=get_current_user(),
        active="reports",
        report_section="billing",
    )


@bp.get("/uss/reports/fot")
def uss_reports_fot():
    return render_template(
        "uss/fot.html",
        user=get_current_user(),
        active="reports",
        report_section="fot",
    )


@bp.get("/admin/reference")
def admin_reference():
    return render_template("admin/reference.html", user=get_current_user())


@bp.get("/admin/sso")
def admin_sso():
    return render_template("admin/sso.html", user=get_current_user())
