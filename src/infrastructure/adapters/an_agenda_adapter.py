"""
Agenda adapter — public sittings, past and upcoming.

Source: {base}/static/openData/repository/{legislature}/vp/reunions/Agenda.xml.zip
        (~9 MB, ~7 700 files under xml/reunion/; only seance_type + RUAN are kept)
"""

from datetime import date, datetime

from lxml import etree

from src.domain.entities.agenda_item import AgendaItem
from src.domain.entities.agenda_point import AgendaPoint
from src.domain.ports.sources.agenda_source import AgendaSource
from src.domain.ports.sources.archive_source import ArchiveSource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.adapters.archive_cache import load_archive
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient

ARCHIVE_PATH = "/static/openData/repository/{legislature}/vp/reunions/Agenda.xml.zip"
MEMBER_PREFIX = "xml/reunion/"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
SITTING_TYPE = "seance_type"
ASSEMBLEE_PREFIX = "RUAN"  # RUSN = Sénat, skipped


def _text(node, path: str) -> str | None:
    if node is None:
        return None
    found = node.find("/".join(f"{{*}}{part}" for part in path.split("/")))
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _datetime(value: str | None) -> datetime | None:
    # "2024-07-19T15:00:00.000+02:00" — ISO 8601 with offset, nothing to guess
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _is_sitting(content: bytes) -> bool:
    """Cheap pre-check on the file head, before any XML parsing."""
    head = content[:400]
    return b'xsi:type="seance_type"' in head and b"<uid>" + ASSEMBLEE_PREFIX.encode() in head


class AnAgendaAdapter(AgendaSource, ArchiveSource):
    def __init__(
        self, http: HttpClient, storage: RawStoragePort, base_url: str, *, refresh: bool = False
    ) -> None:
        self._http = http
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._cache: dict[int, bytes] = {}
        self._refresh = refresh
        self.last_s3_key: str | None = None

    def archive_url(self, legislature: int) -> str:
        return self._base_url + ARCHIVE_PATH.format(legislature=legislature)

    def archive_key(self, legislature: int) -> str:
        return f"raw/agenda/{legislature}/Agenda.xml.zip"

    async def refresh_archive(self, legislature: int) -> str:
        self._cache[legislature] = await load_archive(
            self._http,
            self._storage,
            url=self.archive_url(legislature),
            key=self.archive_key(legislature),
            refresh=True,
        )
        return self.archive_key(legislature)

    async def _archive(self, legislature: int) -> bytes:
        # One archive per legislature, read once per run; S3 first, the AN site otherwise.
        if legislature not in self._cache:
            self._cache[legislature] = await load_archive(
                self._http,
                self._storage,
                url=self.archive_url(legislature),
                key=self.archive_key(legislature),
                content_type="application/zip",
                refresh=self._refresh,
            )
            self.last_s3_key = self.archive_key(legislature)
        return self._cache[legislature]

    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[AgendaItem]:
        payload = await self._archive(legislature)
        items: list[AgendaItem] = []
        for _, content in iter_zip_members(payload, prefix=MEMBER_PREFIX):
            if not _is_sitting(content):
                continue
            item = self._parse_reunion(content, legislature)
            if item is None:
                continue
            day = item.start_at.date()
            if (since and day < since) or (until and day > until):
                continue
            items.append(item)
            if limit is not None and len(items) >= limit:
                break
        items.sort(key=lambda i: i.start_at)
        return items

    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> AgendaItem | None:
        payload = await self._archive(legislature)
        for name, content in iter_zip_members(payload, prefix=f"{MEMBER_PREFIX}{uid}"):
            if name.endswith(f"{uid}.xml"):
                return self._parse_reunion(content, legislature)
        return None

    # -- parsing: pure functions, covered by tests/adapters --------------------

    @classmethod
    def _parse_reunion(cls, xml: bytes, legislature: int) -> AgendaItem | None:
        root = etree.fromstring(xml)
        uid = _text(root, "uid")
        start = _datetime(_text(root, "timeStampDebut"))
        if root.get(XSI_TYPE) != SITTING_TYPE or not uid or not uid.startswith(ASSEMBLEE_PREFIX):
            return None
        if start is None:
            return None

        points = [
            p
            for p in (
                cls._parse_point(node, position)
                for position, node in enumerate(root.findall("{*}ODJ/{*}pointsODJ/{*}pointODJ"), 1)
            )
            if p
        ]
        return AgendaItem(
            uid=uid,
            legislature=legislature,
            start_at=start,
            end_at=_datetime(_text(root, "timeStampFin")),
            location=_text(root, "lieu/libelleLong"),
            state=_text(root, "cycleDeVie/etat"),
            debate_uid=_text(root, "compteRenduRef"),
            session_rank=_text(root, "identifiants/quantieme"),
            session_number=_int(_text(root, "identifiants/numSeanceJO")),
            points=points,
        )

    @staticmethod
    def _parse_point(node, position: int) -> AgendaPoint | None:
        uid = _text(node, "uid")
        if not uid:
            return None
        return AgendaPoint(
            uid=uid,
            title=_text(node, "objet"),
            kind=_text(node, "typePointODJ"),
            state=_text(node, "cycleDeVie/etat"),
            order=position,
            dossier_refs=[
                d.text.strip()
                for d in node.findall("{*}dossiersLegislatifsRefs/{*}dossierRef")
                if d.text and d.text.strip()
            ],
        )
