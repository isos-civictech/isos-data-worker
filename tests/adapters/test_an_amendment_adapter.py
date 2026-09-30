"""Parsing tests against real amendment files."""

from datetime import date
from pathlib import Path

import pytest

from src.domain.entities.amendment import AmendmentAuthorType, AmendmentStatus
from src.infrastructure.adapters.an_amendment_adapter import AnAmendmentAdapter

FIXTURES = Path(__file__).parent.parent / "fixtures" / "an"
SEANCE = FIXTURES / "amendement_AMANR5L17PO838901B2681P0D1N000225.xml"
COMMISSION = FIXTURES / "amendement_commission_rapporteur.xml"


@pytest.fixture
def seance():
    return AnAmendmentAdapter._parse(SEANCE.read_bytes(), dossier_uid="DLR5L17N53940")


def test_identity(seance):
    assert seance.uid == "AMANR5L17PO838901B2681P0D1N000225"
    assert seance.legislature == 17
    assert seance.dossier_uid == "DLR5L17N53940", "comes from the archive path"
    assert seance.texte_uid == "PRJLANR5L17B2681"
    assert seance.number == "225"
    assert seance.rectification == 0
    assert seance.parent_uid is None


def test_author(seance):
    assert seance.author_type == AmendmentAuthorType.DEPUTY
    assert seance.deputy_uid == "PA841701"
    assert seance.group_uid == "PO845439"
    assert len(seance.cosigner_uids) == 36
    assert seance.signatories[:2] == ["Mme Balage El Mariky", "M. Amirshahi"]
    assert len(seance.signatories) == 37


def test_target_and_outcome(seance):
    assert seance.examined_by == "AN" and seance.in_public_sitting
    assert (seance.division_title, seance.division_position) == ("Article 2", "A")
    assert seance.article_ref == "Article 2"
    assert seance.alinea is None, "the whole article is targeted"
    assert seance.content == "Supprimer cet article."
    assert "<" not in seance.summary and "&" not in seance.summary
    assert seance.summary.startswith("Cet amendement du groupe écologiste")
    assert seance.deposited_at == date(2026, 6, 25)
    assert (seance.state, seance.sub_state, seance.sort) == ("Discuté", "Rejeté", "Rejeté")
    assert seance.status == AmendmentStatus.REJECTED
    assert seance.sorted_at.tzinfo is not None


def test_commission_rapporteur():
    a = AnAmendmentAdapter._parse(COMMISSION.read_bytes(), dossier_uid="DLR5L17N53940")
    assert a.author_type == AmendmentAuthorType.RAPPORTEUR
    assert not a.in_public_sitting
    assert a.examined_by == "CION_LOIS"
    assert a.article_ref == "Article 3"
    assert a.alinea == "Après l'alinéa 34"
