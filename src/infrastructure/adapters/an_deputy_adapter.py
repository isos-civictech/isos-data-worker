"""
AMO30 adapter — every actor of the legislature: deputies past and present,
ministers, and the political groups.

Source: {base}/static/openData/repository/{legislature}/amo/
        tous_acteurs_mandats_organes_xi_legislature/
        AMO30_tous_acteurs_tous_mandats_tous_organes_historique.xml.zip
        (~16 MB: 3 100 acteurs, 10 800 organes — of all legislatures, so filter)

The archive uses a default XML namespace; every lookup goes through `_text()`,
which ignores it. An <acteur> holds many <mandat> nodes: ASSEMBLEE ones are
seats, GP ones the group, MINISTERE ones a government post, the rest is ignored.
"""

from datetime import date

from lxml import etree

from src.domain.entities.deputy import Deputy
from src.domain.entities.government_role import GovernmentRole
from src.domain.entities.mandate import Mandate
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.ports.sources.archive_source import ArchiveSource
from src.domain.ports.sources.deputy_source import DeputySource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.legislatures import legislature_end, legislature_start
from src.domain.shared.validators import Legislature
from src.infrastructure.adapters.archive_cache import load_archive
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient

ARCHIVE_PATH = (
    "/static/openData/repository/{legislature}/amo/"
    "tous_acteurs_mandats_organes_xi_legislature/"
    "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.xml.zip"
)
GROUP_CODE_TYPE = "GP"
SEAT = "ASSEMBLEE"
MINISTRY = "MINISTERE"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
POST_MANDATE_TYPE = "MandatSimple_Type"  # a MandatMission_Type is "en mission", not a post
# Official portraits, not in the archive but derivable from the uid.
PHOTO_URL = "https://www2.assemblee-nationale.fr/static/tribun/{legislature}/photos/{number}.jpg"


def _text(node, path: str) -> str | None:
    """Namespace-agnostic text lookup (`{*}` matches any namespace)."""
    if node is None:
        return None
    found = node.find("/".join(f"{{*}}{part}" for part in path.split("/")))
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _int(node, path: str) -> int | None:
    raw = _text(node, path)
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def _date(node, path: str) -> date | None:
    raw = _text(node, path)
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _overlaps(mandat, start: date | None, end: date | None) -> bool:
    """Does the mandat's period intersect [start, end]? Open ends never close."""
    m_start, m_end = _date(mandat, "dateDebut"), _date(mandat, "dateFin")
    return (end is None or m_start is None or m_start <= end) and (
        start is None or m_end is None or m_end >= start
    )


def _gender(civ: str | None) -> str | None:
    # "M." / "Mme" — both start with M, so no slicing.
    return {"M.": "M", "Mme": "F"}.get(civ or "")


class AnDeputyAdapter(DeputySource, ArchiveSource):
    def __init__(
        self, http: HttpClient, storage: RawStoragePort, base_url: str, *, refresh: bool = False
    ) -> None:
        self._http = http
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._cache: dict[int, bytes] = {}
        self._refresh = refresh
        self._organe_names: dict[int, dict[str, str]] = {}
        self.last_s3_key: str | None = None

    def archive_url(self, legislature: int) -> str:
        return self._base_url + ARCHIVE_PATH.format(legislature=legislature)

    def archive_key(self, legislature: int) -> str:
        return f"raw/deputies/{legislature}/AMO30.xml.zip"

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

    def _organes(self, legislature: int, payload: bytes) -> dict[str, str]:
        """uid -> libelle for every organe, to name ministries."""
        if legislature not in self._organe_names:
            names = {}
            for _, content in iter_zip_members(payload, prefix="xml/organe/", suffix=".xml"):
                root = etree.fromstring(content)
                uid, name = _text(root, "uid"), _text(root, "libelle")
                if uid and name:
                    names[uid] = name
            self._organe_names[legislature] = names
        return self._organe_names[legislature]

    async def fetch_political_groups(self, legislature: Legislature) -> list[PoliticalGroupRef]:
        payload = await self._archive(legislature)
        groups = (
            self._parse_organe(content)
            for _, content in iter_zip_members(payload, prefix="xml/organe/", suffix=".xml")
        )
        return [g for g in groups if g is not None and g.legislature == legislature]

    async def fetch_all(self, legislature: Legislature, limit: int | None = None) -> list[Deputy]:
        payload = await self._archive(legislature)
        organes = self._organes(legislature, payload)
        deputies: list[Deputy] = []
        for _, content in iter_zip_members(payload, prefix="xml/acteur/", suffix=".xml"):
            deputy = self._parse_acteur(content, legislature, organes)
            if deputy is None:
                continue
            deputies.append(deputy)
            if limit is not None and len(deputies) >= limit:
                break
        return deputies

    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Deputy | None:
        payload = await self._archive(legislature)
        for name, content in iter_zip_members(payload, prefix=f"xml/acteur/{uid}"):
            if name.endswith(f"{uid}.xml"):
                return self._parse_acteur(content, legislature, self._organes(legislature, payload))
        return None

    # -- parsing: pure functions, covered by tests/adapters --------------------

    @staticmethod
    def _parse_organe(xml: bytes) -> PoliticalGroupRef | None:
        root = etree.fromstring(xml)
        if _text(root, "codeType") != GROUP_CODE_TYPE:
            return None
        uid, name = _text(root, "uid"), _text(root, "libelle")
        if not uid or not name:
            return None
        return PoliticalGroupRef(
            uid=uid,
            name=name,
            short_name=_text(root, "libelleAbrege"),
            legislature=_int(root, "legislature"),
        )

    @classmethod
    def _parse_acteur(
        cls, xml: bytes, legislature: int, organes: dict[str, str] | None = None
    ) -> Deputy | None:
        """None when the actor played no part in this legislature (AMO30 has them all)."""
        root = etree.fromstring(xml)
        civil = root.find("{*}etatCivil/{*}ident")

        uid = _text(root, "uid")
        first_name = _text(civil, "prenom")
        last_name = _text(civil, "nom")
        if not uid or not first_name or not last_name:
            return None

        mandates = cls._build_mandates(root, uid, legislature)
        roles = cls._build_government_roles(root, uid, legislature, organes or {})
        if not mandates and not roles:
            return None

        return Deputy(
            uid=uid,
            first_name=first_name,
            last_name=last_name,
            birth_date=_text(root, "etatCivil/infoNaissance/dateNais"),
            gender=_gender(_text(civil, "civ")),
            profession=_text(root, "profession/libelleCourant"),
            photo_url=PHOTO_URL.format(legislature=legislature, number=uid.removeprefix("PA")),
            mandates=mandates,
            government_roles=roles,
        )

    @staticmethod
    def _build_mandates(acteur, deputy_uid: str, legislature: int) -> list[Mandate]:
        """One Mandate per ASSEMBLEE seat of the legislature, with its overlapping group."""
        mandats = acteur.findall("{*}mandats/{*}mandat")
        seats = [
            m
            for m in mandats
            if _text(m, "typeOrgane") == SEAT and _int(m, "legislature") == legislature
        ]
        groups = [
            m
            for m in mandats
            if _text(m, "typeOrgane") == GROUP_CODE_TYPE and _int(m, "legislature") == legislature
        ]
        out = []
        for seat in seats:
            uid = _text(seat, "uid")
            if not uid:
                continue
            start, end = _date(seat, "dateDebut"), _date(seat, "dateFin")
            overlapping = [g for g in groups if _overlaps(g, start, end)]
            group = max(overlapping, key=lambda g: _date(g, "dateDebut") or date.min, default=None)
            place = seat.find("{*}election/{*}lieu")
            out.append(
                Mandate(
                    uid=uid,
                    deputy_uid=deputy_uid,
                    legislature=legislature,
                    mandate_start=start,
                    mandate_end=end,
                    group_uid=_text(group, "organes/organeRef"),
                    constituency_number=_int(place, "numCirco"),
                    department_name=_text(place, "departement"),
                    department_number=_text(place, "numDepartement"),
                    seat_number=_int(seat, "mandature/placeHemicycle"),
                )
            )
        out.sort(key=lambda m: m.mandate_start or date.min)
        return out

    @staticmethod
    def _build_government_roles(
        acteur, deputy_uid: str, legislature: int, organes: dict[str, str]
    ) -> list[GovernmentRole]:
        """MINISTERE posts overlapping the legislature (they carry no legislature field)."""
        since, until = legislature_start(legislature), legislature_end(legislature)
        roles = []
        for m in acteur.findall("{*}mandats/{*}mandat"):
            if _text(m, "typeOrgane") != MINISTRY or m.get(XSI_TYPE) != POST_MANDATE_TYPE:
                continue
            if not _overlaps(m, since, until) or not _text(m, "uid"):
                continue
            ministry_uid = _text(m, "organes/organeRef")
            roles.append(
                GovernmentRole(
                    uid=_text(m, "uid"),
                    deputy_uid=deputy_uid,
                    title=_text(m, "infosQualite/libQualiteSex"),
                    ministry_uid=ministry_uid,
                    ministry=organes.get(ministry_uid or ""),
                    start=_date(m, "dateDebut"),
                    end=_date(m, "dateFin"),
                )
            )
        roles.sort(key=lambda r: r.start or date.min)
        return roles
