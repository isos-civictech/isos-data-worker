"""Parsing tests against real dossier files."""

from datetime import date
from pathlib import Path

import pytest

from src.domain.entities.law import LawStatus, LawType
from src.infrastructure.adapters.an_law_adapter import AnLawAdapter

FIXTURES = Path(__file__).parent.parent / "fixtures" / "an"
PROMULGATED = FIXTURES / "dossier_DLR5L17N53940.json"  # projet de loi, full navette
REPORT = FIXTURES / "dossier_DLR5L17N52422.json"  # rapport d'information: not a law


@pytest.fixture
def law():
    return AnLawAdapter._parse_dossier(PROMULGATED.read_bytes())


def test_dossier_fields(law):
    assert law.dossier_uid == "DLR5L17N53940"
    assert law.legislature == 17
    assert law.title.startswith("Projet de loi sur la justice criminelle")
    assert law.procedure_code == "1"
    assert law.initiator_uids == ["PA643210"]
    assert law.senate_url.startswith("http://www.senat.fr/")


def test_domain_rules(law):
    assert law.is_law
    assert law.law_type == LawType.BILL
    assert law.status == LawStatus.PROMULGATED
    assert law.texte_uid == "PRJLSNR5S479B0456", "first deposited text"
    assert law.deposited_at == date(2026, 3, 18)


def test_stages_follow_the_navette(law):
    assert [s.code for s in law.stages] == ["SN1", "AN1", "CMP", "CC", "PROM"]
    assert [s.order for s in law.stages] == [1, 2, 3, 4, 5]
    an1 = law.stages[1]
    assert an1.label == "1ère lecture (2ème assemblée saisie)"
    assert an1.started_at == date(2026, 4, 15)
    assert an1.examined_at == date(2026, 4, 29), "first commission meeting"
    assert an1.concluded_at == date(2026, 7, 7)
    assert (an1.decision, an1.decision_code) == ("modifié", "TSORTF05")
    assert an1.texte_uid == "PRJLANR5L17B2681"
    assert an1.sitting_refs[0] == "RUANR5L17S2026IDS30781"
    assert len(an1.sitting_refs) == 6
    assert an1.is_reading and not law.stages[3].is_reading


def test_report_is_kept_but_not_a_law():
    report = AnLawAdapter._parse_dossier(REPORT.read_bytes())
    assert report.procedure_code == "19"
    assert not report.is_law
    assert report.law_type is None


def test_commission_text_on_the_reading(law):
    an1 = law.stages[1]
    assert an1.commission_texte_uid is None, "the AN commission adopted no text here"
    assert law.stages[0].commission_texte_uid == "PRJLSNR5S479BTC0521"


def test_document_gives_the_texte_number():
    texte = AnLawAdapter._parse_document((FIXTURES / "document_PRJLANR5L17B2681.json").read_bytes())
    assert texte.uid == "PRJLANR5L17B2681"
    assert texte.dossier_uid == "DLR5L17N53940"
    assert texte.number == 2681
    assert texte.kind == "PRJL" and texte.is_law_text
    assert texte.is_assemblee and not texte.is_commission_text
    assert texte.deposited_at == date(2026, 4, 15)
    assert texte.organe_uids == ["PO838901"]
