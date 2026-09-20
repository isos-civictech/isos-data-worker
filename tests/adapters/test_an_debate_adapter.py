"""Parsing tests against a trimmed real Syceron file. Assertions are on entities."""

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from src.domain.entities.intervention import SpeakerType
from src.infrastructure.adapters.an_debate_adapter import (
    AnDebateAdapter,
    _parse_date,
    _speaker_type,
    _texte_number,
)
from src.infrastructure.http.client import HttpClient
from tests.adapters.test_an_deputy_adapter import InMemoryStorage

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "an" / "compte_rendu_CRSANR5L17S2025O1N037.xml"
)
BASE = "https://data.assemblee-nationale.fr"
ARCHIVE_URL = AnDebateAdapter(None, None, BASE).archive_url(17)


def _archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xml/compteRendu/CRSANR5L17S2025O1N037.xml", FIXTURE.read_bytes())
    return buffer.getvalue()


@pytest.fixture
def debate():
    return AnDebateAdapter._parse_compte_rendu(FIXTURE.read_bytes(), 17)


# ── pure helpers ──────────────────────────────────────────────────────────────


def test_syceron_date_is_paris_local_time():
    """14:00 in Paris in November is 13:00 UTC; the result must not depend on the host."""
    parsed = _parse_date("20241106140000000")
    assert parsed.tzinfo is not None
    assert parsed.astimezone(UTC) == datetime(2024, 11, 6, 13, 0, tzinfo=UTC)
    assert _parse_date("garbage") is None
    assert _parse_date(None) is None


def test_bibard_keeps_only_the_text_number():
    """The attribute is free text; only the number is a usable join key."""
    assert _texte_number(" (n[[o]]\xa01043 rectifié)") == "1043"
    assert _texte_number(" 2765") == "2765"
    assert _texte_number(" ") is None


def test_speaker_type_rules():
    assert _speaker_type("PA1", "M. Untel", "ministre délégué") == SpeakerType.MINISTER
    assert _speaker_type("PA1", "Mme la présidente", None) == SpeakerType.PRESIDENT
    assert _speaker_type("PA1", "M. Untel", None) == SpeakerType.DEPUTY
    assert _speaker_type(None, "Un invité", None) == SpeakerType.OTHER


# ── whole file ────────────────────────────────────────────────────────────────


def test_sitting_metadata(debate):
    assert debate.uid == "CRSANR5L17S2025O1N037"
    assert debate.session_number == 37
    assert debate.date.astimezone(UTC) == datetime(2024, 11, 6, 13, 0, tzinfo=UTC)
    assert debate.title == "Première séance du mercredi 06 novembre 2024"


def test_points_are_flattened_with_parent_and_level(debate):
    by_uid = {p.uid: p for p in debate.points}
    child = by_uid["3555259"]
    assert child.parent_uid == "3555308"
    assert child.level == 99
    assert child.kind == "SUSP_SEANCE_1_1"
    assert by_uid["3555181"].parent_uid is None


def test_point_carries_its_kind_and_title(debate):
    first = debate.points[0]
    assert first.kind == "QG_1_1"
    assert first.title == "Indemnisation des incorporés de force en Alsace"


def test_speeches_have_speaker_and_type(debate):
    speeches = debate.points[0].interventions
    assert [i.speaker_type for i in speeches] == [
        SpeakerType.PRESIDENT,
        SpeakerType.DEPUTY,
        SpeakerType.DEPUTY,
    ]
    assert speeches[1].deputy_uid == "PA794810"
    assert speeches[1].speaker_name == "Mme Louise Morel"
    assert speeches[1].content.startswith("Monsieur le ministre")


def test_heckles_without_speaker_are_dropped(debate):
    """The fixture holds an INTERRUPTION paragraph with no <orateur>."""
    assert all(i.speaker_name for p in debate.points for i in p.interventions)


# ── through HTTP ──────────────────────────────────────────────────────────────


@respx.mock
async def test_fetch_all_and_archive_stored():
    storage = InMemoryStorage()
    respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=_archive()))

    async with HttpClient() as http:
        adapter = AnDebateAdapter(http, storage, BASE)
        debates = await adapter.fetch_all(17)

    assert [d.uid for d in debates] == ["CRSANR5L17S2025O1N037"]
    assert "raw/debates/17/syceron.xml.zip" in storage.objects


def test_date_range_filter_reads_the_file_head():
    from datetime import date

    from src.infrastructure.adapters.an_debate_adapter import _in_range

    content = FIXTURE.read_bytes()  # sitting on 2024-11-06
    assert _in_range(content, None, None)
    assert _in_range(content, date(2024, 11, 6), date(2024, 11, 6))
    assert _in_range(content, date(2024, 11, 1), None)
    assert not _in_range(content, date(2024, 11, 7), None)
    assert not _in_range(content, None, date(2024, 11, 5))
