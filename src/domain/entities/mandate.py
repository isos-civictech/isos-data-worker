"""
Mandate entity — represents a deputy's term in a specific legislature.

Sources:
    ZIP (XML): https://data.assemblee-nationale.fr/static/openData/repository/
            {legislature}/amo/deputes_actifs_mandats_actifs_organes/
            AMO10_deputes_actifs_mandats_actifs_organes.xml.zip

XML field mapping (inside acteur/PA{id}.xml):
    uid                  → acteur/mandats/mandat/uid
    deputy_uid           → acteur/uid  (parent file)
    legislature          → acteur/mandats/mandat/legislature
    mandate_start        → acteur/mandats/mandat/dateDebut
    mandate_end          → acteur/mandats/mandat/dateFin  (empty = still active)
    seat_number          → acteur/mandats/mandat/preseance
    group_acronym        → acteur/mandats/mandat/organes/organeRef    → organe/PO{id}.xml/libelleAbrege
    group_name           → acteur/mandats/mandat/organes/organeRef    → organe/PO{id}.xml/libelle
    constituency_number  → acteur/mandats/mandat/election/lieu/numCirco
    department_name      → acteur/mandats/mandat/election/lieu/nomDep
    department_number    → acteur/mandats/mandat/election/lieu/numDep
"""

from datetime import date
from pydantic import BaseModel, computed_field
from src.domain.shared.validators import Legislature, NotBlankStr


class Mandate(BaseModel):
    """
    Represents a single term in the National Assembly.
    One person (Deputy) → one Mandate per legislature.
    """

    uid: NotBlankStr
    deputy_uid: NotBlankStr

    legislature: Legislature
    mandate_start: date | None = None
    mandate_end: date | None = None  # None or future = still active

    group_acronym: NotBlankStr
    group_name: NotBlankStr

    constituency_number: int
    department_name: NotBlankStr
    department_number: NotBlankStr

    seat_number: int | None = None

    @computed_field
    @property
    def is_active(self) -> bool:
        return self.mandate_end is None or self.mandate_end > date.today()

    class Config:
        from_attributes = True
