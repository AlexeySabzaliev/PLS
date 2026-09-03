"""Тесты import-from-billings и PLS_FREEZE_REFERENCE."""
from datetime import date
from unittest.mock import patch

from app.db import db
from app.seeds.fix_ariston_canonical import fix_ariston_canonical
from app.seeds.import_from_billings import import_from_billings


def test_fix_ariston_skipped_when_frozen(app):
    with app.app_context():
        app.config["PLS_FREEZE_REFERENCE"] = True
        report = fix_ariston_canonical(dry_run=True)
        assert any("PLS_FREEZE_REFERENCE" in line for line in report.actions)


def test_fix_ariston_force_overrides_freeze(app):
    with app.app_context():
        app.config["PLS_FREEZE_REFERENCE"] = True
        report = fix_ariston_canonical(dry_run=True, force=True)
        assert not any("заморожены" in line for line in report.actions)


@patch("app.seeds.import_from_billings._fetch")
@patch("app.seeds.import_from_billings.import_staff_from_billings")
def test_import_from_billings_dry_run_reference(mock_staff, mock_fetch, app):
    mock_staff.return_value.actions = []
    mock_staff.return_value.imported = 0
    mock_staff.return_value.skipped = 0
    mock_fetch.side_effect = [
        [{"id": 1, "name": "Тест-клиент", "security_name": None, "is_active": True}],
        [{"id": 1, "code": "testwh", "name": "Тест-склад", "security_visit_place": None, "is_active": True}],
        [],
        [],
        [],
    ]
    with app.app_context():
        report = import_from_billings(dry_run=True, only="reference")
        assert report.dry_run is True
        assert any("клиент" in line.lower() for line in report.actions)
        assert any("склад" in line.lower() for line in report.actions)


@patch("app.seeds.import_from_billings._fetch")
def test_import_shifts_dry_run_vehicle_and_daily(mock_fetch, app):
    """Паритет Billings: vehicle_operations + operation_daily_totals в only=shifts."""
    from app.seeds.import_from_billings import ImportReport, _import_shifts

    mock_fetch.side_effect = [
        [
            {
                "id": 9001,
                "contract_id": 1,
                "warehouse_id": 1,
                "operation_date": date(2026, 7, 15),
                "tractor_plate": "А111АА78",
                "trailer_plate": None,
                "plate_number": "А111АА78",
                "operation_type_code": "inbound",
                "seal_number": None,
                "torg2_number": None,
                "volume_document_m3": 12,
                "handling_type_code": "manual",
                "extra_handling_m3": None,
                "extra_document_set_qty": None,
                "registered_at": None,
                "departed_at": None,
                "report_quantities": {},
                "source": "import",
            }
        ],
        [
            {
                "contract_id": 1,
                "warehouse_id": 1,
                "report_date": date(2026, 7, 15),
                "billing_line_code": "is_custom",
                "quantity": 5,
            }
        ],
    ]

    with app.app_context():
        from app.modules.reference.models import Contract, Warehouse

        contract = Contract.query.filter_by(id=1).first()
        wh = Warehouse.query.filter_by(id=1).first()
        assert contract is not None
        assert wh is not None

        report = ImportReport(dry_run=True, only="shifts")
        _import_shifts(
            report,
            contracts={1: contract},
            warehouses={1: wh},
            skip_existing=False,
        )
        assert report.imported == 2
        assert any("ТС" in line for line in report.actions)
        assert any("суточное" in line for line in report.actions)
