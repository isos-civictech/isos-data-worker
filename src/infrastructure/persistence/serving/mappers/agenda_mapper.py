"""`raw.agenda_item` row -> `public.debate` row (a sitting as scheduled)."""

from typing import Any

from src.infrastructure.persistence.serving.slug import slugify

RANK_WORD = {"Première": "1", "Deuxième": "2", "Troisième": "3", "Unique": "unique"}
FRENCH_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
FRENCH_MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def sitting_title(rank: str | None, start) -> str:
    """'Première séance du mercredi 06 novembre 2024' — the compte rendu's own wording."""
    day = f"{FRENCH_DAYS[start.weekday()]} {start:%d} {FRENCH_MONTHS[start.month - 1]} {start:%Y}"
    return f"{rank or 'Séance'} séance du {day}" if rank else f"Séance du {day}"


def sitting_slug(rank: str | None, start) -> str:
    """'seance-2024-11-06-1' — readable, unique per day and rank."""
    suffix = RANK_WORD.get(rank or "", slugify(rank or "seance"))
    return f"seance-{start:%Y-%m-%d}-{suffix}"


def debate_row_from_agenda(raw: dict[str, Any], status: str) -> dict[str, Any]:
    start = raw["start_at"]
    return {
        "session_number": raw["session_number"] or 0,
        "title": sitting_title(raw["session_rank"], start),
        "session_date": start,
        "calendar_status": status,
        "slug": sitting_slug(raw["session_rank"], start),
        "external_id": raw["uid"],
    }
