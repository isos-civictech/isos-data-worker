"""
Syceron adapter — sittings, agenda points and speeches.

Source: {base}/static/openData/repository/{legislature}/vp/syceronbrut/syseron.xml.zip
        (~55 MB, ~600 files under xml/compteRendu/)

Points nest through <point> inside <point>; they are flattened with `level`
and `parent_uid`. Paragraphs without an <orateur> are heckles and are dropped.
"""

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from lxml import etree

from src.domain.entities.debate import Debate, SessionType
from src.domain.entities.debate_point import DebatePoint
from src.domain.entities.intervention import Intervention, SpeakerType
from src.domain.ports.sources.debate_source import DebateSource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient

ARCHIVE_PATH = "/static/openData/repository/{legislature}/vp/syceronbrut/syseron.xml.zip"
MEMBER_PREFIX = "xml/compteRendu/"
# Syceron times are Paris local time with no offset. Made explicit here, or the
# result depends on the timezone of whatever machine runs the worker.
PARIS = ZoneInfo("Europe/Paris")
# The sitting date sits in the first ~500 bytes: cheap to read without parsing.
_DATE_HEAD = re.compile(rb"<dateSeance>(\d{8})")


def _text(node, path: str) -> str | None:
    if node is None:
        return None
    found = node.find("/".join(f"{{*}}{part}" for part in path.split("/")))
    if found is None:
        return None
    joined = " ".join("".join(found.itertext()).split())
    return joined or None


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _parse_date(raw: str | None) -> datetime | None:
    # "20241106140000000" — seconds precision plus three ms digits
    if not raw or len(raw) < 14:
        return None
    try:
        return datetime.strptime(raw[:14], "%Y%m%d%H%M%S").replace(tzinfo=PARIS)
    except ValueError:
        return None


def _texte_number(bibard: str | None) -> str | None:
    """' (n[[o]] 1043 rectifié)' -> '1043'. Only the number is a usable key."""
    if not bibard:
        return None
    digits = "".join(ch for ch in bibard if ch.isdigit())
    return digits or None


def _in_range(content: bytes, since: date | None, until: date | None) -> bool:
    """Filter on the sitting date read from the file head, before any XML parsing."""
    if since is None and until is None:
        return True
    match = _DATE_HEAD.search(content[:2000])
    if not match:
        return True  # unknown date: let the parser decide
    sitting = datetime.strptime(match.group(1).decode(), "%Y%m%d").date()
    return (since is None or sitting >= since) and (until is None or sitting <= until)


def _speaker_type(deputy_uid: str | None, name: str | None, quality: str | None) -> SpeakerType:
    if quality:
        return SpeakerType.MINISTER
    if name and "président" in name.lower():
        return SpeakerType.PRESIDENT
    if deputy_uid and deputy_uid.startswith("PA"):
        return SpeakerType.DEPUTY
    return SpeakerType.OTHER


class AnDebateAdapter(DebateSource):
    def __init__(self, http: HttpClient, storage: RawStoragePort, base_url: str) -> None:
        self._http = http
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._cache: dict[int, bytes] = {}
        self.last_s3_key: str | None = None

    def archive_url(self, legislature: int) -> str:
        return self._base_url + ARCHIVE_PATH.format(legislature=legislature)

    async def _archive(self, legislature: int) -> bytes:
        if legislature not in self._cache:
            payload = await self._http.get_bytes(self.archive_url(legislature))
            self.last_s3_key = await self._storage.put(
                f"raw/debates/{legislature}/syceron.xml.zip",
                payload,
                content_type="application/zip",
            )
            self._cache[legislature] = payload
        return self._cache[legislature]

    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
        since: date | None = None,
        until: date | None = None,
    ) -> list[Debate]:
        payload = await self._archive(legislature)
        debates: list[Debate] = []
        for _, content in iter_zip_members(payload, prefix=MEMBER_PREFIX):
            if not _in_range(content, since, until):
                continue
            parsed = self._parse_compte_rendu(content, legislature)
            if parsed is not None:
                debates.append(parsed)
                if limit is not None and len(debates) >= limit:
                    break
        return debates

    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Debate | None:
        payload = await self._archive(legislature)
        for name, content in iter_zip_members(payload, prefix=f"{MEMBER_PREFIX}{uid}"):
            if name.endswith(f"{uid}.xml"):
                return self._parse_compte_rendu(content, legislature)
        return None

    # -- parsing: pure functions, covered by tests/adapters --------------------

    @classmethod
    def _parse_compte_rendu(cls, xml: bytes, legislature: int) -> Debate | None:
        root = etree.fromstring(xml)
        uid = _text(root, "uid")
        meta = root.find("{*}metadonnees")
        date = _parse_date(_text(meta, "dateSeance"))
        if not uid or date is None:
            return None

        contenu = root.find("{*}contenu")
        points: list[DebatePoint] = []
        nivpoints: list[int] = []  # parallel to `points`, parsing-time only
        if contenu is not None:
            for point in contenu.findall("{*}point"):
                cls._collect_points(point, parent_uid=None, out=points, levels=nivpoints)

        return Debate(
            uid=uid,
            legislature=_int(_text(meta, "legislature")) or legislature,
            session_number=_int(_text(meta, "numSeance")),
            session_type=SessionType.PUBLIC_SESSION,
            date=date,
            title=_text(contenu, "quantiemes/journee"),
            points=points,
        )

    @classmethod
    def _collect_points(
        cls, node, *, parent_uid: str | None, out: list[DebatePoint], levels: list[int]
    ) -> None:
        """
        Flatten a <point> and its nested <point>s.

        The AN nests some points in the XML and merely *sequences* others after
        a heading (nivpoint 1 = section title, 2 = topic, 99 = procedural).
        Both cases become one tree: a point's parent is the enclosing <point>
        when nested, otherwise the last preceding point with a smaller nivpoint.
        """
        uid = node.get("id_syceron")
        if not uid:
            return
        nivpoint = _int(node.get("nivpoint")) or 1
        if parent_uid is None:
            parent_uid = cls._section_parent(out, levels, nivpoint)

        number = _texte_number(node.get("bibard"))
        out.append(
            DebatePoint(
                uid=uid,
                parent_uid=parent_uid,
                title=_text(node, "texte"),
                kind=node.get("code_grammaire") or None,
                order=_int(node.get("ordre_absolu_seance")) or 0,
                texte_refs=[number] if number else [],
                interventions=[
                    i for i in map(cls._parse_paragraphe, node.findall("{*}paragraphe")) if i
                ],
            )
        )
        levels.append(nivpoint)
        for child in node.findall("{*}point"):
            cls._collect_points(child, parent_uid=uid, out=out, levels=levels)

    @staticmethod
    def _section_parent(points: list[DebatePoint], levels: list[int], nivpoint: int) -> str | None:
        """Nearest preceding point with a smaller nivpoint, i.e. its heading."""
        for previous, level in zip(reversed(points), reversed(levels), strict=True):
            if level < nivpoint:
                return previous.uid
        return None

    @staticmethod
    def _parse_paragraphe(node) -> Intervention | None:
        uid = node.get("id_syceron")
        orateur = node.find("{*}orateurs/{*}orateur")
        content = _text(node, "texte")
        if not uid or orateur is None or not content:
            return None  # heckle, stage direction, or empty

        deputy_uid = (node.get("id_acteur") or "").strip() or None
        if deputy_uid in ("-1", ""):
            deputy_uid = None
        name = _text(orateur, "nom")
        quality = _text(orateur, "qualite")

        return Intervention(
            uid=uid,
            deputy_uid=deputy_uid,
            speaker_name=name,
            speaker_type=_speaker_type(deputy_uid, name, quality),
            content=content,
            order_in_debate=_int(node.get("ordre_absolu_seance")),
        )
