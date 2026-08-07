"""
DebatePoint — one agenda item inside a Debate, discussing one specific Law.
All Interventions inside a DebatePoint are about ONE Law only.

Source: Syceron XML
XML path: compteRendu/pointsOrdreJour/point
    uid       → point/uid
    texte_uid → point/textesAssocies/refText  ← the Law pivot (PION..., PRJL...)
    title     → point/libelle
    order     → position in the pointsOrdreJour list (1-indexed)

"""
from pydantic import BaseModel
from src.domain.entities.intervention import Intervention
from src.domain.shared.validators import NotBlankStr


class DebatePoint(BaseModel):
    uid: NotBlankStr
    texte_uid: str | None = None
    title: str | None = None
    order: int
    interventions: list[Intervention] = []

    class Config:
        from_attributes = True