"""Тесты синхронизации м³ обработки."""
from app.modules.uss.services.shift_handling import infer_handling_from_volumes, sync_handling_m3_updates


def test_infer_handling_from_volumes():
    assert infer_handling_from_volumes(10, 0, 0, 0) == "manual"
    assert infer_handling_from_volumes(0, 12, 0, 0) == "mechanized"
    assert infer_handling_from_volumes(0, 0, 0, 0) == ""


def test_sync_handling_m3_inbound_manual():
    rq = sync_handling_m3_updates({
        "operation_type_code": "inbound",
        "handling_type_code": "manual",
        "volume_document_m3": 15.5,
    })
    assert rq["inbound_manual_m3"] == 15.5
    assert rq["inbound_mech_m3"] == 0
    assert rq["outbound_manual_m3"] == 0


def test_sync_handling_m3_outbound_mech():
    rq = sync_handling_m3_updates({
        "operation_type_code": "outbound",
        "handling_type_code": "mechanized",
        "volume_document_m3": 8,
    })
    assert rq["outbound_mech_m3"] == 8.0
    assert rq["inbound_manual_m3"] == 0
