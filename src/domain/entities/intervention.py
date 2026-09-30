"""
Intervention — one speech inside a DebatePoint.

XML field mapping (point/paragraphe):
    uid              → @id_syceron
    deputy_uid       → @id_acteur                ("PA…"; ministers are often deputies too)
    speaker_name     → paragraphe/orateurs/orateur/nom
    speaker_type     → derived: orateur/qualite non-empty → MINISTER,
                                nom contains "président" → PRESIDENT,
                                @id_acteur starts with PA → DEPUTY
    content          → paragraphe/texte
    order_in_debate  → @ordre_absolu_seance

Paragraphs without an <orateur> (code_grammaire INTERRUPTION_*) are heckles
with no attributable speaker; they are not kept.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SpeakerType(StrEnum):
    DEPUTY = "deputy"
    MINISTER = "minister"
    PRESIDENT = "president"
    OTHER = "other"


class Intervention(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: str | None = None
    deputy_uid: str | None = None
    speaker_name: str | None = None
    speaker_type: SpeakerType = SpeakerType.OTHER
    content: str | None = None
    order_in_debate: int | None = None
