"""
DebatePoint — one agenda item (point d'ordre du jour) inside a sitting.

Points form a tree through `parent_uid`: a section heading ("Questions au
Gouvernement") holds its topics, a text under discussion holds its articles.

XML field mapping (compteRendu/contenu//point):
    uid         → @id_syceron
    title       → point/texte
    kind        → @code_grammaire       ("QG_1_1" questions au gouvernement,
                                         "DISC_ARTICLES_*" discussion d'un texte,
                                         "SUSP_SEANCE_1_1" suspension…)
    order       → @ordre_absolu_seance
    texte_refs  → @bibard               the text NUMBER ("2765", "n° 1043 rectifié"),
                                        never a uid — the join to a law goes
                                        through the number once laws are collected
"""

from pydantic import BaseModel, ConfigDict

from src.domain.entities.intervention import Intervention


class DebatePoint(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: str | None = None
    parent_uid: str | None = None
    title: str | None = None
    kind: str | None = None
    order: int = 0
    texte_refs: list[str] = []
    interventions: list[Intervention] = []
