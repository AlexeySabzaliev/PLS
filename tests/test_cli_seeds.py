"""Тесты CLI и миграций."""
import pytest

from app.modules.reference.models import Client, Contract, Role, User
from app.modules.uss.models import VehicleOperation
from app.modules.reference.client_names import CANONICAL_ARISTON_CLIENT
from app.seeds.ariston_august import resolve_august_excel_path
from app.seeds.bootstrap import seed_demo, seed_reference
from app.seeds.fix_ariston_canonical import CANONICAL_CONTRACT_NUMBER


def test_migration_and_seed_reference(migrated_app):
    with migrated_app.app_context():
        seed_reference()
        assert Role.query.filter_by(code="admin").first() is not None
        assert Role.query.count() >= 6

        # Идемпотентность
        seed_reference()
        assert Role.query.filter_by(code="admin").count() == 1


@pytest.mark.skipif(
    resolve_august_excel_path() is None,
    reason="Нет Ariston billing 08.2026.xlsx (Billings fixtures)",
)
def test_seed_demo_creates_contract(migrated_app):
    with migrated_app.app_context():
        stats = seed_demo()
        assert Client.query.filter_by(name=CANONICAL_ARISTON_CLIENT).first() is not None
        assert Client.query.filter_by(name="Аристон").first() is None
        assert User.query.filter_by(email="admin@bsh-ru.ru").first() is not None
        assert Contract.query.filter(
            Contract.number.ilike(f"%{CANONICAL_CONTRACT_NUMBER}%")
        ).first() is not None
        assert Contract.query.filter_by(number="STR-OH-ARISTON").first() is None
        assert stats["vehicles"] >= 50
        assert VehicleOperation.query.count() >= stats["vehicles"]
