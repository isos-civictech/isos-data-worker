"""
AgendaPoint — one item on a sitting's agenda (point d'ordre du jour).

XML field mapping (reunion/ODJ/pointsODJ/pointODJ):
    uid           → pointODJ/uid
    title         → pointODJ/objet
    kind          → pointODJ/typePointODJ         "Discussion", "Questions au Gouvernement"…
    state         → pointODJ/cycleDeVie/etat
    dossier_refs  → pointODJ/dossiersLegislatifsRefs/dossierRef[]   ("DLR5L17N53818") — the law link
"""

from pydantic import BaseModel, ConfigDict


class AgendaPoint(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: str | None = None
    title: str | None = None
    kind: str | None = None
    state: str | None = None
    order: int = 0
    dossier_refs: list[str] = []
