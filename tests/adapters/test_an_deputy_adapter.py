"""Parsing tests against trimmed real AMO files. Assertions are on entities."""

import io
import zipfile
from pathlib import Path

import httpx
import pytest
import respx

from src.domain.ports.storage import RawStoragePort
from src.infrastructure.adapters.an_deputy_adapter import AnDeputyAdapter
from src.infrastructure.http.client import HttpClient

FIXTURES = Path(__file__).parent.parent / "fixtures" / "an"


class InMemoryStorage(RawStoragePort):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key, body, content_type="application/octet-stream") -> str:
        self.objects[key] = body
        return key

    async def exists(self, key) -> bool:
        return key in self.objects


def _archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xml/acteur/PA1592.xml", (FIXTURES / "acteur_PA1592.xml").read_bytes())
        archive.writestr("xml/acteur/PA9999.xml", (FIXTURES / "acteur_PA9999.xml").read_bytes())
        archive.writestr("xml/organe/PO845401.xml", (FIXTURES / "organe_PO845401.xml").read_bytes())
        archive.writestr("xml/organe/PO420120.xml", (FIXTURES / "organe_PO420120.xml").read_bytes())
    return buffer.getvalue()


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


# ── pure parsing, no HTTP ─────────────────────────────────────────────────────


def test_namespace_does_not_swallow_every_field():
    """Without namespace handling every field is silently None."""
    deputy = AnDeputyAdapter._parse_acteur((FIXTURES / "acteur_PA1592.xml").read_bytes(), 17)

    assert deputy is not None
    assert deputy.uid == "PA1592"
    assert deputy.first_name == "Jean-Luc"
    assert deputy.last_name == "Mélenchon"
    assert deputy.profession == "Professeur"
    assert (
        str(deputy.photo_url)
        == "https://www2.assemblee-nationale.fr/static/tribun/17/photos/1592.jpg"
    )


def test_seat_and_group_come_from_two_different_mandat_nodes():
    """Seat data from the ASSEMBLEE mandat, group uid from the GP one."""
    deputy = AnDeputyAdapter._parse_acteur((FIXTURES / "acteur_PA1592.xml").read_bytes(), 17)
    mandate = deputy.mandates[0]

    # from ASSEMBLEE
    assert mandate.uid == "PM1592001"
    assert mandate.department_name == "Bouches-du-Rhône"
    assert mandate.constituency_number == 4
    assert mandate.seat_number == 219
    # from the ACTIVE GP, not the closed one, and not the ASSEMBLEE organeRef
    assert mandate.group_uid == "PO845401"


def test_closed_group_mandate_is_ignored():
    """A deputy who switched group has two GP mandats; only the open one counts."""
    deputy = AnDeputyAdapter._parse_acteur((FIXTURES / "acteur_PA1592.xml").read_bytes(), 17)
    assert deputy.mandates[0].group_uid != "PO000000"


def test_deputy_without_department_does_not_crash():
    """Deputies elected abroad have no department."""
    deputy = AnDeputyAdapter._parse_acteur((FIXTURES / "acteur_PA9999.xml").read_bytes(), 17)

    assert deputy is not None
    assert deputy.gender == "F", '"Mme" must not be read as "M"'
    assert deputy.mandates[0].department_name is None
    assert deputy.mandates[0].constituency_number is None


def test_only_political_groups_are_kept():
    group = AnDeputyAdapter._parse_organe((FIXTURES / "organe_PO845401.xml").read_bytes())
    commission = AnDeputyAdapter._parse_organe((FIXTURES / "organe_PO420120.xml").read_bytes())

    assert group is not None
    assert group.short_name == "LFI-NFP"
    assert commission is None, "a commission is not a political group"


# ── with HTTP simulated by respx ──────────────────────────────────────────────


BASE = "https://data.assemblee-nationale.fr"
ARCHIVE_URL = AnDeputyAdapter(None, None, BASE).archive_url(17)


@respx.mock
async def test_fetch_all_reads_the_archive(storage):
    respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=_archive()))

    async with HttpClient() as http:
        adapter = AnDeputyAdapter(http, storage, BASE)
        deputies = await adapter.fetch_all(17)

    assert {d.uid for d in deputies} == {"PA1592", "PA9999"}


@respx.mock
async def test_raw_archive_is_kept_for_traceability(storage):
    respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=_archive()))

    async with HttpClient() as http:
        adapter = AnDeputyAdapter(http, storage, BASE)
        await adapter.fetch_all(17)

    assert "raw/deputies/17/AMO30.xml.zip" in storage.objects


@respx.mock
async def test_archive_is_downloaded_once_for_both_passes(storage):
    """Groups then deputies: two passes, one download."""
    route = respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=_archive()))

    async with HttpClient() as http:
        adapter = AnDeputyAdapter(http, storage, BASE)
        await adapter.fetch_political_groups(17)
        await adapter.fetch_all(17)

    assert route.call_count == 1


@respx.mock
async def test_limit_stops_early(storage):
    respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=_archive()))

    async with HttpClient() as http:
        adapter = AnDeputyAdapter(http, storage, BASE)
        assert len(await adapter.fetch_all(17, limit=1)) == 1


def test_minister_with_two_seats_in_the_legislature():
    """Real AMO30 case: left for the government, came back, then left again."""
    organes = {"PO873654": "Ministère des sports", "PO847734": "Ministère délégué au tourisme"}
    deputy = AnDeputyAdapter._parse_acteur(
        (FIXTURES / "acteur_PA795120_minister.xml").read_bytes(), 17, organes
    )
    assert deputy.uid == "PA795120" and deputy.is_deputy and deputy.is_minister
    assert [m.uid for m in deputy.mandates] == ["PM858429", "PM843344"] or [
        m.uid for m in deputy.mandates
    ] == ["PM843344", "PM858429"]
    assert all(m.group_uid == "PO845454" for m in deputy.mandates), "group overlaps each seat"
    # The first post started under the 16th but ran into the 17th: kept.
    assert [r.uid for r in deputy.government_roles] == ["PM834789", "PM847787", "PM873690"]
    current = deputy.government_roles[-1]
    assert (current.title, current.ministry, current.end) == (
        "Ministre",
        "Ministère des sports",
        None,
    )


def test_actor_outside_the_legislature_is_skipped():
    """AMO30 lists every actor since 1958: only those with a part in this legislature matter."""
    deputy = AnDeputyAdapter._parse_acteur(
        (FIXTURES / "acteur_PA795120_minister.xml").read_bytes(), 15, {}
    )
    assert deputy is None, "no seat in the 15th, and the posts all ended before the 17th opened"
