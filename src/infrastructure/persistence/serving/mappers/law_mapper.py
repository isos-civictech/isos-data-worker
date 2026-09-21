"""`raw.law` (+ stages) -> `public.law` / `public.law_reading` rows."""

from typing import Any

from src.domain.entities.law import Law
from src.domain.entities.law_texte import LawTexte
from src.domain.entities.legislative_stage import LegislativeStage
from src.infrastructure.persistence.serving.slug import slugify

DOSSIER_PAGE = "https://www.assemblee-nationale.fr/dyn/{legislature}/dossiers/{uid}"
NAME_MAX = 255

# Stage code -> (chamber, reading number). NLEC = nouvelle lecture, LDEF =
# lecture définitive: numbered after the second reading so they sort last.
READINGS = {
    "AN1": ("national_assembly", 1),
    "AN2": ("national_assembly", 2),
    "ANNLEC": ("national_assembly", 3),
    "ANLDEF": ("national_assembly", 4),
    "ANLUNI": ("national_assembly", 1),
    "SN1": ("senate", 1),
    "SN2": ("senate", 2),
    "SNNLEC": ("senate", 3),
    "SNLDEF": ("senate", 4),
    "SNLUNI": ("senate", 1),
    "CMP": ("cmp", 1),
}


def law_from_raw(
    row: dict[str, Any],
    stage_rows: list[dict[str, Any]],
    texte_rows: list[dict[str, Any]] = (),
) -> Law:
    """Rebuild the entity so status, type and number come from the domain, not from SQL."""
    stages = [
        LegislativeStage(uid=s["stage_uid"], order=s["position"], **_stage_fields(s))
        for s in stage_rows
    ]
    textes = [LawTexte(**{k: t[k] for k in LawTexte.model_fields if k in t}) for t in texte_rows]
    return Law(stages=stages, textes=textes, **{k: row[k] for k in Law.model_fields if k in row})


def _stage_fields(s: dict[str, Any]) -> dict[str, Any]:
    keep = set(LegislativeStage.model_fields) - {"uid", "order"}
    return {k: s[k] for k in keep if k in s}


def short_name(title: str) -> str:
    """Cut on a word so VARCHAR(255) never truncates mid-word."""
    if len(title) <= NAME_MAX:
        return title
    cut = title[: NAME_MAX - 1].rsplit(" ", 1)[0]
    return cut + "…"


def law_row(law: Law, *, legislature_id: int) -> dict[str, Any]:
    return {
        "legislature_id": legislature_id,
        "type": law.law_type.value,
        "number": law.number,
        "name": short_name(law.title),
        "title": law.title,
        "slug": slugify(law.title, max_length=120),
        "status": law.status.value,
        "deposited_at": law.deposited_at,
        "source_url": DOSSIER_PAGE.format(legislature=law.legislature, uid=law.dossier_uid),
        "external_id": law.dossier_uid,
    }


def reading_status(stage: LegislativeStage) -> str:
    if stage.rejected:
        return "rejected"
    if stage.decision_code:
        return "adopted"
    return "in_discussion" if stage.examined_at else "submitted"


def reading_calendar_status(stage: LegislativeStage) -> str:
    if stage.concluded_at:
        return "completed"
    return "ongoing" if stage.examined_at else "scheduled"


def law_reading_row(stage: LegislativeStage, *, law_id: int) -> dict[str, Any] | None:
    reading = READINGS.get(stage.code)
    if reading is None:
        return None
    chamber, number = reading
    return {
        "law_id": law_id,
        "chamber": chamber,
        "reading_number": number,
        "status": reading_status(stage),
        "calendar_status": reading_calendar_status(stage),
        "started_at": stage.started_at,
        "concluded_at": stage.concluded_at,
    }
