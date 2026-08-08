"""
DebatePoint — one agenda item inside a Debate, discussing one specific Law.
All Interventions inside a DebatePoint are about ONE Law only.

Source: Syceron XML
XML path: compteRendu/pointsOrdreJour/point
    uid         → point/uid
    texte_refs  → point/textesAssocies/refText  ← the Law pivot (PION..., PRJL...)
    title       → point/libelle
    order       → position in the pointsOrdreJour list (1-indexed)

"""
from pydantic import BaseModel, ConfigDict
from src.domain.entities.intervention import Intervention
from src.domain.shared.validators import NotBlankStr


class DebatePoint(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: str | None = None
    texte_refs: list[str] = []
    title: str | None = None
    order: int = 0
    interventions: list[Intervention] = []
