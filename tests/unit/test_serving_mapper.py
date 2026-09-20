"""The serving mapper's output IS the contract with public: assert the dict."""
from datetime import date

from src.infrastructure.persistence.serving.mappers.deputy_mapper import deputy_row, mandate_row

RAW_DEPUTY = {
    "uid": "PA1592",
    "first_name": "Jean-Luc",
    "last_name": "Mélenchon",
    "birth_date": date(1951, 8, 19),
    "gender": "M",
    "profession": "Professeur",
    "photo_url": "https://www2.assemblee-nationale.fr/static/tribun/17/photos/1592.jpg",
}
RAW_MANDATE = {
    "constituency_number": 4,
    "department_name": "Bouches-du-Rhône",
    "mandate_start": date(2024, 7, 7),
    "mandate_end": None,
}


def test_deputy_row_adapts_to_public():
    row = deputy_row(RAW_DEPUTY, RAW_MANDATE)

    assert row["slug"] == "jean-luc-melenchon"
    assert row["external_id"] == "PA1592"
    assert row["picture"].endswith("/1592.jpg")
    assert row["source_url"] == "https://www.assemblee-nationale.fr/dyn/deputes/PA1592"
    assert row["constituency"] == "4"
    assert row["department"] == "Bouches-du-Rhône"


def test_fields_without_a_public_column_are_dropped():
    row = deputy_row(RAW_DEPUTY, RAW_MANDATE)
    assert "gender" not in row
    assert "profession" not in row


def test_deputy_without_mandate():
    row = deputy_row(RAW_DEPUTY, None)
    assert row["constituency"] is None
    assert row["department"] is None


def test_mandate_row_resolves_integer_fks():
    row = mandate_row(RAW_MANDATE, deputy_id=7, legislature_id=1, political_group_id=3)
    assert row == {
        "deputy_id": 7,
        "legislature_id": 1,
        "political_group_id": 3,
        "started_at": date(2024, 7, 7),
        "ended_at": None,
    }
