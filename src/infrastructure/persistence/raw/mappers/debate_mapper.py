"""Entity -> `raw` row. Pure transcription."""

from typing import Any

from src.domain.entities.debate import Debate
from src.domain.entities.debate_point import DebatePoint
from src.domain.entities.intervention import Intervention


def debate_row(debate: Debate) -> dict[str, Any]:
    return {
        "uid": debate.uid,
        "legislature": debate.legislature,
        "session_number": debate.session_number,
        "session_type": debate.session_type.value,
        "date": debate.date,
        "title": debate.title,
    }


def point_row(point: DebatePoint, *, debate_uid: str) -> dict[str, Any]:
    return {
        "debate_uid": debate_uid,
        "point_uid": point.uid,
        "parent_uid": point.parent_uid,
        "title": point.title,
        "kind": point.kind,
        "position": point.order,
        "texte_refs": point.texte_refs,
    }


def intervention_row(intervention: Intervention, *, debate_point_id: int) -> dict[str, Any]:
    return {
        "debate_point_id": debate_point_id,
        "uid": intervention.uid,
        "deputy_uid": intervention.deputy_uid,
        "speaker_name": intervention.speaker_name,
        "speaker_type": intervention.speaker_type.value,
        "content": intervention.content,
        "order_in_debate": intervention.order_in_debate,
    }
