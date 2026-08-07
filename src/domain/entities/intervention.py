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
from enum import Enum
from pydantic import BaseModel
from src.domain.shared.validators import NotBlankStr


class SpeakerType(str, Enum):
    DEPUTY = "deputy"
    MINISTER = "minister"
    PRESIDENT = "president"
    OTHER = "other"


class Intervention(BaseModel):
    uid: str | None = None
    deputy_uid: str | None = None
    speaker_name: NotBlankStr
    speaker_type: SpeakerType = SpeakerType.OTHER
    content: NotBlankStr
    order_in_debate: int

    class Config:
        from_attributes = True