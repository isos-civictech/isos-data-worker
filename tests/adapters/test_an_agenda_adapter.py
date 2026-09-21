"""Parsing tests against a trimmed real Agenda file."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.domain.entities.agenda_item import AgendaItem, SessionStatus
from src.infrastructure.adapters.an_agenda_adapter import AnAgendaAdapter, _is_sitting

FIXTURES = Path(__file__).parent.parent / "fixtures" / "an"
SITTING = FIXTURES / "reunion_RUANR5L17S2026IDS30663.xml"
SENAT = FIXTURES / "reunion_senat_RUSNR5L17S2026IDS30745.xml"


@pytest.fixture
def item():
    return AnAgendaAdapter._parse_reunion(SITTING.read_bytes(), 17)


def test_head_check_keeps_assemblee_sittings_only():
    assert _is_sitting(SITTING.read_bytes())
    assert not _is_sitting(SENAT.read_bytes()), "Sénat sittings are out of scope"


def test_senat_is_skipped_by_the_parser_too():
    assert AnAgendaAdapter._parse_reunion(SENAT.read_bytes(), 17) is None


def test_sitting_fields(item):
    assert item.uid == "RUANR5L17S2026IDS30663"
    assert item.start_at.tzinfo is not None
    assert item.start_at.astimezone(UTC) == datetime(2026, 6, 3, 19, 30, tzinfo=UTC)
    assert item.state == "Confirmé"
    assert item.session_rank == "Deuxième"
    assert item.session_number == 262
    assert item.debate_uid == "CRSANR5L17S2026O1N262", "the link to the compte rendu"


def test_agenda_points_carry_the_law_dossier(item):
    confirmed = [p for p in item.points if p.state == "Confirmé"]
    assert confirmed
    assert confirmed[0].dossier_refs == ["DLR5L17N54148"]
    assert confirmed[0].kind == "Suite de la discussion"
    assert item.dossier_refs == ["DLR5L17N54148"]


def test_status_rules():
    now = datetime.now(tz=UTC)
    base = dict(uid="X", legislature=17)
    assert AgendaItem(**base, start_at=now + timedelta(days=1)).status == SessionStatus.SCHEDULED
    assert AgendaItem(**base, start_at=now - timedelta(hours=1)).status == SessionStatus.ONGOING
    assert AgendaItem(**base, start_at=now - timedelta(days=1)).status == SessionStatus.COMPLETED
    assert (
        AgendaItem(**base, start_at=now + timedelta(days=1), state="Supprimé").status
        == SessionStatus.CANCELLED
    )
    assert (
        AgendaItem(**base, start_at=now - timedelta(hours=1), debate_uid="CR").status
        == SessionStatus.COMPLETED
    ), "a compte rendu means the sitting is over"
