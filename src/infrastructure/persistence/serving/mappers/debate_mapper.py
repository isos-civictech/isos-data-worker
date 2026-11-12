"""`raw.debate` row -> `public.debate` row."""

from collections.abc import Iterable
from html import escape
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
        "source_url": SITTING_PAGE.format(legislature=raw["legislature"], uid=uid),
    }


def transcript_html(rows: Iterable[dict[str, Any]]) -> str | None:
    """Full text of a sitting as HTML, from its interventions in speaking order.

    `rows` carry point_uid, point_title, speaker_name and content, already
    sorted. A heading is written each time the agenda point changes. None when
    the sitting has no speech (the editor field then stays empty, not "<p></p>").
    """
    parts: list[str] = []
    current_point = None
    for row in rows:
        text = (row["content"] or "").strip()
        if not text:
            continue
        if row["point_uid"] != current_point:
            current_point = row["point_uid"]
            if row["point_title"]:
                parts.append(f"<h2>{escape(row['point_title'])}</h2>")
        speaker = escape(row["speaker_name"] or "Intervenant")
        parts.append(f"<p><strong>{speaker}</strong> : {escape(text)}</p>")
    return "".join(parts) or None
