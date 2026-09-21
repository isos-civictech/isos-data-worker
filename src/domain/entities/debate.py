"""
Debate — one public sitting (séance), made of ordered DebatePoints.

Source: Syceron XML
    ZIP: https://data.assemblee-nationale.fr/static/openData/repository/{legislature}/vp/syceronbrut/syseron.xml.zip
    Members: xml/compteRendu/CRSANR5L{legislature}S{year}{O|E}{n}N{num}.xml
             (O = ordinary session, E = extraordinary)

XML field mapping (default namespace http://schemas.assemblee-nationale.fr/referentiel):
    uid            → compteRendu/uid                          ("CRSANR5L17S2025O1N037")
    legislature    → compteRendu/metadonnees/legislature
    session_number → compteRendu/metadonnees/numSeance
    date           → compteRendu/metadonnees/dateSeance     "20241106140000000" (%Y%m%d%H%M%S + ms)
    title          → compteRendu/contenu/quantiemes/journee "Première séance du mercredi 06 …"
    points         → compteRendu/contenu/point[] (nested via nivpoint)

S3 key: raw/debates/{legislature}/syceron.xml.zip
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
    title: str | None = None
    points: list[DebatePoint] = []
    s3_key: str | None = None

    @computed_field
    @property
    def texte_numbers(self) -> list[str]:
        """Every text number (numéro de dépôt) discussed, in order, deduplicated."""
        seen: set[str] = set()
        result: list[str] = []
        for point in self.points:
            for ref in point.texte_refs:
                if ref not in seen:
                    seen.add(ref)
                    result.append(ref)
        return result
