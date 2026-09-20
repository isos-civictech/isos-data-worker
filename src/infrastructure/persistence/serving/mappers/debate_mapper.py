"""`raw.debate` row -> `public.debate` row."""

from typing import Any

from src.infrastructure.persistence.serving.slug import slugify

SITTING_PAGE = "https://www.assemblee-nationale.fr/dyn/{legislature}/comptes-rendus/seance/{uid}"


def debate_row(raw: dict[str, Any]) -> dict[str, Any]:
    uid = raw["uid"]
    date = raw["date"]
    return {
        "session_number": raw["session_number"] or 0,
        "title": raw["title"],
        "session_date": date,
        # A compte rendu only exists once the sitting has happened.
        "calendar_status": "completed",
        # Stable and unique without a lookup: the date, then the sitting uid.
        "slug": f"seance-{date:%Y-%m-%d}-{slugify(uid)}"[:255],
        "raw_s3_key": raw["s3_key"],
        "source_url": SITTING_PAGE.format(legislature=raw["legislature"], uid=uid),
        "external_id": uid,
    }
