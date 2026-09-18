"""
AMO10 adapter — deputies and political groups.

Source: {base}/static/openData/repository/{legislature}/amo/
        deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.xml.zip

The archive uses a default XML namespace; every lookup goes through `_text()`,
which ignores it. An <acteur> holds several <mandat> nodes: ASSEMBLEE is the
seat, the active GP one is the group, the rest is ignored.
"""
from lxml import etree

from src.domain.entities.deputy import Deputy
from src.domain.entities.mandate import Mandate
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.ports.sources.deputy_source import DeputySource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient
from src.infrastructure.persistence.checksum import sha256_bytes

ARCHIVE_PATH = (
    "/static/openData/repository/{legislature}/amo/"
    "deputes_actifs_mandats_actifs_organes/"
    "AMO10_deputes_actifs_mandats_actifs_organes.xml.zip"
)
GROUP_CODE_TYPE = "GP"


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


def _is_active(mandat) -> bool:
    return _text(mandat, "dateFin") is None


def _gender(civ: str | None) -> str | None:
    # "M." / "Mme" — both start with M, so no slicing.
    return {"M.": "M", "Mme": "F"}.get(civ or "")


class AnDeputyAdapter(DeputySource):
    def __init__(self, http: HttpClient, storage: RawStoragePort, base_url: str) -> None:
        self._http = http
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._cache: dict[int, bytes] = {}
        self.last_checksum: str | None = None

    def archive_url(self, legislature: int) -> str:
        return self._base_url + ARCHIVE_PATH.format(legislature=legislature)

    async def _archive(self, legislature: int) -> bytes:
        # Downloaded once, reused for the groups pass and the deputies pass.
        if legislature not in self._cache:
            payload = await self._http.get_bytes(self.archive_url(legislature))
            self.last_checksum = sha256_bytes(payload)
            await self._storage.put(
                f"raw/deputies/{legislature}/AMO10.xml.zip",
                payload,
                content_type="application/zip",
            )
            self._cache[legislature] = payload
        return self._cache[legislature]

    async def fetch_political_groups(self, legislature: Legislature) -> list[PoliticalGroupRef]:
        payload = await self._archive(legislature)
        groups = (
            self._parse_organe(content)
            for _, content in iter_zip_members(payload, prefix="xml/organe/", suffix=".xml")
        )
        return [g for g in groups if g is not None]

    async def fetch_all(self, legislature: Legislature, limit: int | None = None) -> list[Deputy]:
        payload = await self._archive(legislature)
        deputies = (
            self._parse_acteur(content, legislature)
            for _, content in iter_zip_members(
                payload, prefix="xml/acteur/", suffix=".xml", limit=limit
            )
        )
        return [d for d in deputies if d is not None]

    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Deputy | None:
        payload = await self._archive(legislature)
        for name, content in iter_zip_members(payload, prefix=f"xml/acteur/{uid}"):
            if name.endswith(f"{uid}.xml"):
                return self._parse_acteur(content, legislature)
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
    def _parse_acteur(cls, xml: bytes, legislature: int) -> Deputy | None:
        root = etree.fromstring(xml)
        civil = root.find("{*}etatCivil/{*}ident")

        uid = _text(root, "uid")
        first_name = _text(civil, "prenom")
        last_name = _text(civil, "nom")
        if not uid or not first_name or not last_name:
            return None

        mandate = cls._build_mandate(root, uid, legislature)

        return Deputy(
            uid=uid,
            first_name=first_name,
            last_name=last_name,
            birth_date=_text(root, "etatCivil/infoNaissance/dateNais"),
            gender=_gender(_text(civil, "civ")),
            profession=_text(root, "profession/libelleCourant"),
            photo_url=None,
            mandates=[mandate] if mandate else [],
        )

    @staticmethod
    def _build_mandate(acteur, deputy_uid: str, legislature: int) -> Mandate | None:
        """Seat from the ASSEMBLEE mandat, group from the active GP mandat."""
        seat = group = None
        for mandat in acteur.findall("{*}mandats/{*}mandat"):
            kind = _text(mandat, "typeOrgane")
            if kind == "ASSEMBLEE" and seat is None:
                seat = mandat
            elif kind == GROUP_CODE_TYPE and _is_active(mandat):
                group = mandat

        if seat is None:
            return None
        uid = _text(seat, "uid")
        if not uid:
            return None

        place = seat.find("{*}election/{*}lieu")
        return Mandate(
            uid=uid,
            deputy_uid=deputy_uid,
            legislature=_int(seat, "legislature") or legislature,
            mandate_start=_text(seat, "dateDebut"),
            mandate_end=_text(seat, "dateFin"),
            group_uid=_text(group, "organes/organeRef"),
            constituency_number=_int(place, "numCirco"),
            department_name=_text(place, "departement"),
            department_number=_text(place, "numDepartement"),
            seat_number=_int(seat, "mandature/placeHemicycle"),
        )
