from datetime import date

from src.domain.entities.law import Law, LawStatus
from src.domain.entities.legislative_stage import LegislativeStage
from src.infrastructure.persistence.serving.mappers.law_mapper import (
    law_from_raw,
    law_reading_row,
    law_row,
    short_name,
)


def _stage(code, **kw):
    return LegislativeStage(uid=f"D-{code}", code=code, label=code, **kw)


def _law(*stages, **kw):
    fields = dict(dossier_uid="DLR5L17N1", legislature=17, title="Proposition de loi X")
    return Law(**fields, procedure_code=kw.pop("code", "2"), stages=list(stages), **kw)


def test_status_progression():
    assert _law(_stage("AN1", started_at=date(2025, 1, 1))).status == LawStatus.SUBMITTED
    assert (
        _law(_stage("AN1", started_at=date(2025, 1, 1), examined_at=date(2025, 2, 1))).status
        == LawStatus.IN_DISCUSSION
    )
    assert _law(_stage("AN1", decision_code="TSORTF07")).status == LawStatus.REJECTED
    assert _law(_stage("AN1"), _stage("ANLDEF", decision_code="TSORTF01")).status == (
        LawStatus.ADOPTED
    )
    assert _law(_stage("PROM", concluded_at=date(2025, 3, 1))).status == LawStatus.PROMULGATED
    assert _law(_stage("AN1"), withdrawn=True).status == LawStatus.WITHDRAWN


def test_organic_law_type_comes_from_the_title():
    assert _law(code="5").law_type.value == "proposition"
    organic_bill = Law(
        dossier_uid="D", legislature=17, title="Projet de loi organique …", procedure_code="5"
    )
    assert organic_bill.law_type.value == "bill"


def test_short_name_cuts_on_a_word():
    title = "mot " * 100
    name = short_name(title.strip())
    assert len(name) <= 255
    assert name.endswith("mot…")
    assert short_name("court") == "court"


def test_law_row():
    row = law_row(_law(_stage("AN1", started_at=date(2025, 1, 1))), legislature_id=3)
    assert row["type"] == "proposition"
    assert row["status"] == "submitted"
    assert row["slug"] == "proposition-de-loi-x"
    assert row["external_id"] == "DLR5L17N1"
    assert row["deposited_at"] == date(2025, 1, 1)
    assert row["source_url"].endswith("/dyn/17/dossiers/DLR5L17N1")


def test_reading_rows():
    assert law_reading_row(_stage("PROM"), law_id=1) is None, "not a reading"
    row = law_reading_row(
        _stage("SN1", examined_at=date(2025, 1, 5), concluded_at=date(2025, 2, 1),
               decision_code="TSORTF01"),
        law_id=1,
    )  # fmt: skip
    assert (row["chamber"], row["reading_number"]) == ("senate", 1)
    assert (row["status"], row["calendar_status"]) == ("adopted", "completed")
    pending = law_reading_row(_stage("ANNLEC", examined_at=date(2025, 1, 5)), law_id=1)
    assert (pending["reading_number"], pending["status"], pending["calendar_status"]) == (
        3,
        "in_discussion",
        "ongoing",
    )


def test_law_from_raw_rebuilds_the_entity():
    raw = {
        "dossier_uid": "DLR5L17N1",
        "legislature": 17,
        "title": "Projet de loi Y",
        "senate_url": None,
        "procedure_code": "1",
        "procedure_label": "Projet de loi ordinaire",
        "initiator_uids": ["PA1"],
        "withdrawn": False,
        "s3_key": "raw/laws/17/x.zip",
        "id": 42,
        "created_at": None,
    }
    stages = [
        {
            "stage_uid": "DLR5L17N1-AN1",
            "position": 1,
            "code": "AN1",
            "label": "1ère lecture",
            "organe_ref": "PO1",
            "started_at": date(2025, 1, 1),
            "examined_at": None,
            "concluded_at": None,
            "decision": None,
            "decision_code": None,
            "texte_uid": "PRJL1",
            "sitting_refs": ["RUAN1"],
            "id": 7,
        }
    ]
    law = law_from_raw(raw, stages)
    assert law.law_type.value == "bill"
    assert law.stages[0].uid == "DLR5L17N1-AN1"
    assert law.stages[0].order == 1
    assert law.texte_uid == "PRJL1"
