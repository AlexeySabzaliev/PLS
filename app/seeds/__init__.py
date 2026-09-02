"""Сиды справочников и демо-данных."""
from app.seeds.bootstrap import seed_admin, seed_demo, seed_reference

__all__ = ["seed_reference", "seed_admin", "seed_demo"]
