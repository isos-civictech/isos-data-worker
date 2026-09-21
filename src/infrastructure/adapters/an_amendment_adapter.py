"""
Amendment adapter.

Source: {base}/static/openData/repository/{legislature}/loi/amendements_div_legis/
        Amendements.xml.zip  (~340 MB, xml/{dossier}/{texte}/{uid}.xml)
"""

from collections.abc import AsyncIterator
from datetime import date, datetime

from lxml import etree

from src.domain.entities.amendment import Amendment
from src.domain.ports.sources.amendment_source import AmendmentSource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.adapters.html_text import html_to_text, split_names
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient

ARCHIVE_PATH = (
    "/static/openData/repository/{legislature}/loi/amendements_div_legis/Amendements.xml.zip"
)
MEMBER_PREFIX = "xml/"


def _text(node, path: str) -> str | None:
    found = node.find("/".join(f"{{*}}{part}" for part in path.split("/")))
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def _datetime(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


class AnAmendmentAdapter(AmendmentSource):
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
                f"raw/amendments/{legislature}/Amendements.xml.zip",
                payload,
                content_type="application/zip",
            )
            self._cache[legislature] = payload
        return self._cache[legislature]

    async def iter_all(
        self,
        legislature: Legislature,
        *,
        dossier_uid: str | None = None,
        since: date | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Amendment]:
        payload = await self._archive(legislature)
        prefix = f"{MEMBER_PREFIX}{dossier_uid}/" if dossier_uid else MEMBER_PREFIX
        count = 0
        for name, content in iter_zip_members(payload, prefix=prefix, suffix=".xml"):
            amendment = self._parse(content, dossier_uid=name.split("/")[1])
            if amendment is None:
                continue
            if since and (amendment.deposited_at is None or amendment.deposited_at < since):
                continue
            yield amendment
            count += 1
            if limit is not None and count >= limit:
                return

    # -- parsing: pure function, covered by tests/adapters ----------------------

    @staticmethod
    def _parse(xml: bytes, *, dossier_uid: str | None = None) -> Amendment | None:
        root = etree.fromstring(xml)
        uid = _text(root, "uid")
        texte_uid = _text(root, "texteLegislatifRef")
        author_type = _text(root, "signataires/auteur/typeAuteur")
        if not uid or not texte_uid or not author_type:
            return None
        return Amendment(
            uid=uid,
            legislature=int(_text(root, "legislature") or 0),
            dossier_uid=dossier_uid,
            texte_uid=texte_uid,
            examen_ref=_text(root, "examenRef"),
            number=_text(root, "identification/numeroLong"),
            rectification=_int(_text(root, "identification/numeroRect")) or 0,
            examined_by=_text(root, "identification/prefixeOrganeExamen"),
            parent_uid=_text(root, "amendementParentRef"),
            author_type=author_type,
            deputy_uid=_text(root, "signataires/auteur/acteurRef"),
            group_uid=_text(root, "signataires/auteur/groupePolitiqueRef"),
            cosigner_uids=[
                c.text.strip()
                for c in root.findall("{*}signataires/{*}cosignataires/{*}acteurRef")
                if c.text and c.text.strip()
            ],
            signatories=split_names(_text(root, "signataires/libelle")),
            division_title=_text(root, "pointeurFragmentTexte/division/titre"),
            division_type=_text(root, "pointeurFragmentTexte/division/type"),
            division_position=_text(root, "pointeurFragmentTexte/division/avant_A_Apres"),
            alinea=_text(root, "pointeurFragmentTexte/amendementStandard/alinea/alineaDesignation"),
            content=html_to_text(_text(root, "corps/contenuAuteur/dispositif")),
            summary=html_to_text(_text(root, "corps/contenuAuteur/exposeSommaire")),
            deposited_at=_date(_text(root, "cycleDeVie/dateDepot")),
            published_at=_date(_text(root, "cycleDeVie/datePublication")),
            state=_text(root, "cycleDeVie/etatDesTraitements/etat/libelle"),
            sub_state=_text(root, "cycleDeVie/etatDesTraitements/sousEtat/libelle"),
            sort=_text(root, "cycleDeVie/sort"),
            sorted_at=_datetime(_text(root, "cycleDeVie/dateSort")),
        )
