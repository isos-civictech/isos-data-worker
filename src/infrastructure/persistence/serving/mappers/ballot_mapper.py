"""`raw.ballot` / `raw.ballot_vote` rows -> `public.ballot` / `public.deputy_vote` rows."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

BALLOT_TYPES = {"SPO": "public_ordinary", "SPS": "solemn", "MOC": "censure_motion"}
RESULTS = {"adopté": "adopted", "rejeté": "rejected"}
# nonVotant covers "present, did not vote" and "absent": public has one value for both.
POSITIONS = {
    "pour": "for",
    "contre": "against",
    "abstention": "abstention",
    "nonVotant": "absent",
    "nonVotantVolontaire": "absent",
}


def ballot_row(
    raw: dict[str, Any],
    *,
    debate_id: int,
    law_id: int | None,
    amendment_id: int | None,
    reading_id: int | None,
) -> dict[str, Any]:
    return {
        "debate_id": debate_id,
        "law_id": law_id,
        "amendment_id": amendment_id,
        "law_reading_id": reading_id,
        "type": BALLOT_TYPES[raw["kind"]],
        "title": raw["title"],
        "calendar_status": "completed",  # a scrutin is only published once held
        "ballot_date": datetime.combine(raw["date"], datetime.min.time(), tzinfo=PARIS),
        "result": RESULTS.get(raw["result"]),
        "votes_for": raw["for_count"],
        "votes_against": raw["against_count"],
        "abstention_count": raw["abstention_count"],
        "external_id": raw["uid"],
    }


def deputy_vote_row(
    raw: dict[str, Any], *, ballot_id: int, deputy_id: int, group_id: int | None
) -> dict[str, Any]:
    # The "mise au point" states what the deputy meant: that is what we show.
    return {
        "ballot_id": ballot_id,
        "deputy_id": deputy_id,
        "political_group_id": group_id,
        "position": POSITIONS[raw["corrected_position"] or raw["position"]],
    }
