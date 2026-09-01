from flask import Blueprint

bp = Blueprint("health_api", __name__)


@bp.get("/health")
def health():
    return {"status": "ok", "service": "pls"}
