from datetime import date

from src.domain.entities.amendment import Amendment
from src.infrastructure.persistence.serving.mappers.amendment_mapper import (
    amendment_from_raw,
    amendment_row,
)


def test_row_translates_author_and_status():
    a = Amendment(
        uid="AM1",
        legislature=17,
        texte_uid="T",
        number="II-CF146",
        author_type="Rapporteur",
        division_title="Article 3",
        division_position="Après",
        sort="Adopté",
        deposited_at=date(2025, 10, 1),
        examined_by="CION_FIN",
    )
    row = amendment_row(a, law_id=7, deputy_id=None, group_id=None, reading_id=3)
    assert row["author_type"] == "commission", "a rapporteur amends for the commission"
    assert row["status"] == "adopted"
    assert row["article_ref"] == "Après l'article 3"
    assert row["number"] == "II-CF146"
    assert (row["law_id"], row["law_reading_id"]) == (7, 3)
    assert "debate_id" not in row
    assert row["external_id"] == "AM1"


def test_from_raw_ignores_bookkeeping_columns():
    raw = {
        "id": 1,
        "uid": "AM1",
        "legislature": 17,
        "texte_uid": "T",
        "author_type": "Gouvernement",
        "cosigner_uids": [],
        "created_at": None,
        "ingestion_run_id": 4,
    }
    assert amendment_from_raw(raw).author_type.value == "Gouvernement"
