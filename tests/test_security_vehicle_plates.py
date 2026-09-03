"""Разбор госномеров из заявок портала охраны."""

from app.modules.uss.services.security_intranet import (
    _extract_vehicle_number,
    _normalize_row,
    _row_matches_client,
    _row_matches_place,
)
from app.modules.uss.services.vehicle_plates import combine_vehicle_plates, parse_security_vehicle_plates


def test_parse_trailer_marker_pp():
    tractor, trailer = parse_security_vehicle_plates("Вольво У807РС 47 п/п ВА1182 47")
    assert tractor == "У807РС47"
    assert trailer == "ВА118247"

    tractor, trailer = parse_security_vehicle_plates("Мазда В807КВ 47 с/п РВ1182 47")
    assert tractor == "В807КВ47"
    assert trailer == "РВ118247"


def test_parse_slash_separated():
    tractor, trailer = parse_security_vehicle_plates("С582КЕ147/РТ298647")
    assert tractor == "С582КЕ147"
    assert trailer == "РТ298647"


def test_parse_spaced_slash():
    tractor, trailer = parse_security_vehicle_plates("Х506КМ40 / РТ237516")
    assert tractor == "Х506КМ40"
    assert trailer == "РТ237516"


def test_parse_foreign_pair():
    tractor, trailer = parse_security_vehicle_plates("218CS61/K7161")
    assert tractor == "218CS61"
    assert trailer == "K7161"


def test_parse_brand_and_comma():
    tractor, trailer = parse_security_vehicle_plates(
        "Х749КМ799 Mercedes-Benz Actros, Schmitz Cargobull"
    )
    assert tractor == "Х749КМ799"
    assert trailer is None


def test_parse_single_with_brand():
    tractor, trailer = parse_security_vehicle_plates("КамАЗ В905КЕ178")
    assert tractor == "В905КЕ178"
    assert trailer is None


def test_parse_two_plates_without_marker():
    tractor, trailer = parse_security_vehicle_plates("МАН К872РО198 АТ529147")
    assert tractor == "К872РО198"
    assert trailer == "АТ529147"


def test_reject_waybill_placeholder():
    assert parse_security_vehicle_plates("Номер по накладным") == (None, None)
    assert _extract_vehicle_number({"vehicleNumber": "Номер по накладным"}) is None


def test_visit_reason_not_used_for_plate():
    """visitReason не подставляется как госномер (только vehicleNumber/vehiclePlate)."""
    row = {
        "id": "99",
        "visitReason": "Отгрузка по накладным 12345",
        "hasVehicleAccess": True,
    }
    assert _extract_vehicle_number(row) is None
    row["vehicleNumber"] = "КамАЗ В905КЕ178"
    assert _extract_vehicle_number(row) == "В905КЕ178"


def test_extract_from_row_api_fields():
    row = {
        "id": "42",
        "vehicleNumber": "Мазда В807КВ 47 с/п РВ1182 47",
        "hasVehicleAccess": True,
    }
    assert _extract_vehicle_number(row) == "В807КВ47/РВ118247"
    norm = _normalize_row(row)
    assert norm is not None
    assert norm.vehicle_number == "В807КВ47/РВ118247"


def test_client_partial_match():
    row = {
        "contractorName": 'ООО "Аристон Термо Рус"',
        "visitorFullName": "Иванов",
        "visitReason": "Отгрузка",
    }
    assert _row_matches_client(row, 'ООО "Аристон Термо Русь"') is True


def test_client_partial_match_gauff():
    row = {"contractorName": 'ООО "Гауф Рус"', "visitorFullName": ""}
    assert _row_matches_client(row, 'ООО "Гауф Рус"') is True
    assert _row_matches_client(row, 'ООО "Аристон Термо Русь"') is False


def test_trailer_from_separate_field():
    row = {
        "id": "43",
        "vehicleNumber": "КамАЗ В905КЕ178",
        "trailerPlate": "АТ529147",
        "hasVehicleAccess": True,
    }
    assert _extract_vehicle_number(row) == "В905КЕ178/АТ529147"


def test_contractor_short_name_ariston():
    row = {"contractorName": "Аристон", "visitorFullName": "Иванов"}
    assert _row_matches_client(row, 'ООО "Аристон Термо Русь"', "Аристон") is True


def test_mock_rows_unique_per_client():
    from datetime import date

    from app.modules.uss.services.security_intranet import _mock_rows

    day = date(2026, 9, 2)
    a = _mock_rows('ООО "Аристон Термо Русь"', "Склад", day)
    g = _mock_rows('ООО "Гауф Рус"', "Склад", day)
    assert a[0].request_id != g[0].request_id


def test_visit_place_filter():
    row = {"visitPlace": "Склад ГП, ворота 3"}
    assert _row_matches_place(row, "Склад ГП") is True
    assert _row_matches_place(row, "Проходная") is False


def test_combine_truncates_to_db_limit():
    combined = combine_vehicle_plates("А000АА02", "В111ВВ02")
    assert combined == "А000АА02/В111ВВ02"
