"""
Intervention — one speech by one person inside a DebatePoint.

Source: Syceron XML
XML path: compteRendu/interventions/intervention
    uid              → intervention/uid
    deputy_uid       → intervention/acteurRef       (absent if not a deputy)
    speaker_name     → intervention/orateur/nom + prenom
    speaker_type     → derived from acteurRef presence + orateur/qualite
    content          → intervention/texte
    order_in_debate  → intervention/ordre
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