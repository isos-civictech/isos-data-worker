"""
Law adapter — legislative dossiers.

Source: {base}/static/openData/repository/{legislature}/loi/dossiers_legislatifs/
        Dossiers_Legislatifs.json.zip
        (~37 MB; json/dossierParlementaire/DLR*.json is read, json/document/ is not)
"""

import json
from datetime import date, datetime
from typing import Any

from src.domain.entities.law import Law
from src.domain.entities.legislative_stage import LegislativeStage
from src.domain.ports.sources.law_source import LawSource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient

ARCHIVE_PATH = (
    "/static/openData/repository/{legislature}/loi/dossiers_legislatifs/"
    "Dossiers_Legislatifs.json.zip"
)
MEMBER_PREFIX = "json/dossierParlementaire/"
EXAMINATION_ACTS = ("-REUNION", "-RAPPORT", "-SEANCE", "-DEC", "PROM-PUB")


def _as_list(value: Any) -> list:
    """The AN encodes one child as a dict and several as a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _children(acte: dict) -> list[dict]:
    return _as_list((acte.get("actesLegislatifs") or {}).get("acteLegislatif"))


def _walk(acte: dict):
    """The acte itself, then every nested acte, depth first."""
    yield acte
    for child in _children(acte):
        yield from _walk(child)


def _date(value: str | None) -> date | None:
    # "2026-03-18T00:00:00.000+01:00"
    try:
        return datetime.fromisoformat(value).date() if value else None
    except ValueError:
        return None


def _label(acte: dict) -> str | None:
    label = acte.get("libelleActe")
    if isinstance(label, dict):
        return label.get("nomCanonique") or label.get("libelleCourt")
    return label


class AnLawAdapter(LawSource):
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
                f"raw/laws/{legislature}/Dossiers_Legislatifs.json.zip",
                payload,
                content_type="application/zip",
            )
            self._cache[legislature] = payload
        return self._cache[legislature]

    async def fetch_all(self, legislature: Legislature, limit: int | None = None) -> list[Law]:
        payload = await self._archive(legislature)
        laws: list[Law] = []
        for _, content in iter_zip_members(payload, prefix=MEMBER_PREFIX, suffix=".json"):
            # Older dossiers still in navette ship with the archive: keep them.
            law = self._parse_dossier(content)
            if law is None:
                continue
            laws.append(law)
            if limit is not None and len(laws) >= limit:
                break
        return laws

    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Law | None:
        payload = await self._archive(legislature)
        for _, content in iter_zip_members(payload, prefix=f"{MEMBER_PREFIX}{uid}.json"):
            return self._parse_dossier(content)
        return None

    # -- parsing: pure functions, covered by tests/adapters --------------------

    @classmethod
    def _parse_dossier(cls, raw: bytes) -> Law | None:
        dossier = json.loads(raw).get("dossierParlementaire")
        if not dossier or not dossier.get("uid"):
            return None
        procedure = dossier.get("procedureParlementaire") or {}
        initiator = dossier.get("initiateur") or {}
        stages = [
            cls._parse_stage(acte, position)
            for position, acte in enumerate(_children(dossier), 1)
            if acte.get("uid")
        ]
        return Law(
            dossier_uid=dossier["uid"],
            legislature=int(dossier["legislature"]),
            title=(dossier.get("titreDossier") or {}).get("titre") or dossier["uid"],
            senate_url=(dossier.get("titreDossier") or {}).get("senatChemin"),
            procedure_code=procedure.get("code") or "0",
            procedure_label=procedure.get("libelle"),
            initiator_uids=[
                a["acteurRef"]
                for a in _as_list((initiator.get("acteurs") or {}).get("acteur"))
                if a.get("acteurRef")
            ],
            withdrawn=any(a.get("codeActe", "").endswith("-RTRINI") for a in _walk(dossier)),
            stages=stages,
        )

    @staticmethod
    def _parse_stage(acte: dict, position: int) -> LegislativeStage:
        nested = [a for a in _walk(acte) if a is not acte]
        dates = sorted(d for d in (_date(a.get("dateActe")) for a in nested) if d)
        examined = sorted(
            d
            for d in (
                _date(a.get("dateActe"))
                for a in nested
                if a.get("codeActe", "").endswith(EXAMINATION_ACTS)
            )
            if d
        )
        decision = next(
            (a for a in nested if a.get("codeActe", "").endswith(("-DEC", "PROM-PUB"))), None
        )
        deposit = next((a for a in nested if a.get("codeActe", "").endswith("-DEPOT")), None)
        conclusion = (decision or {}).get("statutConclusion") or {}
        return LegislativeStage(
            uid=acte["uid"],
            code=acte.get("codeActe") or acte["uid"],
            label=_label(acte) or acte.get("codeActe") or acte["uid"],
            organe_ref=acte.get("organeRef"),
            order=position,
            started_at=dates[0] if dates else None,
            examined_at=examined[0] if examined else None,
            concluded_at=_date(decision.get("dateActe")) if decision else None,
            decision=conclusion.get("libelle"),
            decision_code=conclusion.get("fam_code"),
            texte_uid=(deposit or {}).get("texteAssocie"),
            sitting_refs=[
                a["reunionRef"]
                for a in nested
                if a.get("codeActe", "").endswith("-SEANCE") and a.get("reunionRef")
            ],
        )
