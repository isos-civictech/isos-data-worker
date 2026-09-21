"""`raw.debate` row -> `public.debate` row."""

from typing import Any

from src.infrastructure.persistence.serving.slug import slugify

SITTING_PAGE = "https://www.assemblee-nationale.fr/dyn/{legislature}/comptes-rendus/seance/{uid}"


def debate_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Fields a compte rendu contributes. `external_id` is set by the projection."""
    uid = raw["uid"]
    date = raw["date"]
    return {
        "session_number": raw["session_number"] or 0,
        "title": raw["title"],
        "session_date": date,
        # A compte rendu only exists once the sitting has happened.
        "calendar_status": "completed",
        # Only used when the sitting has no agenda entry (slug is write-once).
        "slug": f"seance-{date:%Y-%m-%d}-{slugify(uid)}"[:255],
        "raw_s3_key": raw["s3_key"],
        "source_url": SITTING_PAGE.format(legislature=raw["legislature"], uid=uid),
    }
