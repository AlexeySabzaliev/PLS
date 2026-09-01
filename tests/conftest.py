import pytest

from app import create_app
from app.core.auth import hash_password
from app.db import db
from app.modules.processes.schema_resolver import ProcessLine, ProcessLineConfig
from app.modules.processes.templates import EXAMPLE_LINE_CONFIGS
from app.modules.reference.models import (
    Client,
    Contract,
    ContractAmendment,
    ProductType,
    Role,
    TariffRule,
    UnitOfMeasure,
    User,
    UserRole,
    UserWarehouseAccess,
    Warehouse,
)
from datetime import date


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        _seed(application)
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed(app):
    with app.app_context():
        wh = Warehouse(code="spb1", name="СПб-1", is_active=True)
        pt = ProductType(code="RESPONSIBLE_STORAGE", name="Ответственное хранение")
        client = Client(name="Аристон", is_active=True)
        db.session.add_all([wh, pt, client])
        db.session.flush()

        contract = Contract(
            client_id=client.id,
            warehouse_id=wh.id,
            product_type_id=pt.id,
            number="Д-001",
            status="active",
        )
        db.session.add(contract)
        db.session.flush()

        am = ContractAmendment(
            contract_id=contract.id,
            number="ДС-1",
            status="active",
            effective_from=date(2025, 1, 1),
        )
        unit = UnitOfMeasure(code="pcs", name="шт")
        db.session.add_all([am, unit])
        db.session.flush()

        db.session.add(
            TariffRule(
                contract_id=contract.id,
                amendment_id=am.id,
                billing_line_code="valve_gluing",
                name="Подклейка клапанов",
                unit_id=unit.id,
                report_role="warehouse_logistics",
                quantity_source="manual_daily",
                valid_from=date(2025, 1, 1),
            )
        )

        for code, name in [
            ("admin", "Администратор"),
            ("transport_logistics", "Транспортная логистика"),
            ("warehouse_logistics", "Складская логистика"),
        ]:
            db.session.add(Role(code=code, name=name))
        db.session.flush()

        admin = User(
            email="admin@test.local",
            full_name="Админ",
            password_hash=hash_password("admin"),
            is_active=True,
            is_admin=True,
        )
        transport = User(
            email="transport@test.local",
            full_name="Транспорт",
            password_hash=hash_password("test"),
            is_active=True,
        )
        db.session.add_all([admin, transport])
        db.session.flush()

        roles = {r.code: r for r in Role.query.all()}
        db.session.add(UserRole(user_id=admin.id, role_id=roles["admin"].id))
        db.session.add(UserRole(user_id=transport.id, role_id=roles["transport_logistics"].id))
        db.session.add(UserWarehouseAccess(user_id=transport.id, warehouse_id=wh.id))

        line_wh = ProcessLine(
            code="ariston_standard",
            name="Аристон стандарт",
            base_process="warehouse_logistics",
            client_id=client.id,
        )
        line_tr = ProcessLine(
            code="gazprom_logistics",
            name="Газпром логистика",
            base_process="transport_logistics",
        )
        db.session.add_all([line_wh, line_tr])
        db.session.flush()
        db.session.add(ProcessLineConfig(
            process_line_id=line_wh.id,
            config_json=EXAMPLE_LINE_CONFIGS["ariston_standard"],
        ))
        db.session.add(ProcessLineConfig(
            process_line_id=line_tr.id,
            config_json=EXAMPLE_LINE_CONFIGS["gazprom_logistics"],
        ))
        db.session.commit()


@pytest.fixture
def auth_client(client):
    def _login(email, password):
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        return client

    return _login
