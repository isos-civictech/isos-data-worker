"""
Debate — one parliamentary session (an Episode in our Netflix metaphor).

A Debate is structured as ordered DebatePoints.
Each DebatePoint discusses one Law and holds its own Interventions.

Source: Syceron XML
    ZIP: https://data.assemblee-nationale.fr/static/openData/repository/{legislature}/vp/syceronbrut/syseron.xml.zip
    File pattern: CREANR5L{legislature}S{year}E{num}.xml

XML field mapping:
    uid            → compteRendu/uid
    legislature    → compteRendu/legislature
    session_number → compteRendu/numSeance
    session_type   → compteRendu/typeSeance
    date           → compteRendu/dateSeance
    points         → compteRendu/pointsOrdreJour/point[].  ---   each point links to interventions via pointODJRef

S3 path: raw/debates/{legislature}/{year}/{month}/{uid}.xml
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, computed_field
from src.domain.entities.debate_point import DebatePoint
from src.domain.shared.validators import Legislature, NotBlankStr


class SessionType(str, Enum):
    PUBLIC_SESSION = "seance_publique"
    COMMITTEE = "commission"
    OTHER = "other"


class Debate(BaseModel):
    
    uid: NotBlankStr
    legislature: Legislature
    session_number: int | None = None
    session_type: SessionType = SessionType.OTHER
    date: datetime

    
    points: list[DebatePoint] = []

    
    s3_key: str | None = None

    # ── Computed ──────────────────────────────────────────────────────────────
    @computed_field
    @property
    def law_references(self) -> list[str]:
        return [p.texte_uid for p in self.points if p.texte_uid is not None]

    class Config:
        from_attributes = True
