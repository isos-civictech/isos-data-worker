"""Entity -> `raw` row. Pure transcription."""

from typing import Any

from src.domain.entities.agenda_item import AgendaItem
from src.domain.entities.agenda_point import AgendaPoint


def agenda_item_row(item: AgendaItem) -> dict[str, Any]:
    return {
        "uid": item.uid,
        "legislature": item.legislature,
        "start_at": item.start_at,
        "end_at": item.end_at,
        "location": item.location,
        "state": item.state,
        "compte_rendu_uid": item.debate_uid,
        "session_rank": item.session_rank,
        "session_number": item.session_number,
    }


def agenda_point_row(point: AgendaPoint, *, agenda_uid: str) -> dict[str, Any]:
    return {
        "agenda_uid": agenda_uid,
        "point_uid": point.uid,
        "title": point.title,
        "kind": point.kind,
        "state": point.state,
        "position": point.order,
        "dossier_refs": point.dossier_refs,
    }
