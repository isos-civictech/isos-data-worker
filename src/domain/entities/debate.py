"""
Debate — one parliamentary session (an Episode in our Netflix metaphor).

⚠️  AVERTISSEMENT SYCERON XML :
    Le flux Syceron ne suit aucun schéma fixe.
    Le nom du champ date peut être :
    dateSeance | DateSeance | Date_Seance | date_seance

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
    points         → compteRendu/pointsOrdreJour/point[]
                    each point links to its interventions via pointODJRef

S3 path: raw/debates/{legislature}/{year}/{month}/{uid}.xml
"""
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.entities.debate_point import DebatePoint
from src.domain.shared.validators import Legislature, NotBlankStr


class SessionType(StrEnum):
    PUBLIC_SESSION = "seance_publique"
    COMMITTEE = "commission"
    OTHER = "other"


class Debate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

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
        """
        All unique texte_refs values discussed in this debate.--
        """
        seen = set()
        result = []
        for point in self.points:
            for ref in point.texte_refs:
                if ref not in seen:
                    seen.add(ref)
                    result.append(ref)
        return result