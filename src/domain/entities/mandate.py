"""
Mandate entity — represents a deputy's term in a specific legislature.

Sources:
    ZIP (XML): https://data.assemblee-nationale.fr/static/openData/repository/
            {legislature}/amo/deputes_actifs_mandats_actifs_organes/
            AMO10_deputes_actifs_mandats_actifs_organes.xml.zip

    typeOrgane = ASSEMBLEE  → the seat. Source of uid, dates, geography, preseance.
    typeOrgane = GP         → the political group. Source of group_uid only.
                              A deputy who switches group has two GP mandats:
                              take the active one (dateFin empty or in the future).
    typeOrgane = GA / COMPER / COMNL / MISINFO / …  → ignored.

The XML uses a DEFAULT NAMESPACE (http://schemas.assemblee-nationale.fr/referentiel).

XML field mapping (inside acteur/PA{id}.xml):
    deputy_uid           → acteur/uid  (parent file)

    -- from the ASSEMBLEE mandat --
    uid                  → mandat/uid
    legislature          → mandat/legislature
    mandate_start        → mandat/dateDebut
    mandate_end          → mandat/dateFin  (empty = still active)
    seat_number          → mandat/preseance
    constituency_number  → mandat/election/lieu/numCirco
    department_name      → mandat/election/lieu/nomDep
    department_number    → mandat/election/lieu/numDep

    -- from the active GP mandat --
    group_uid            → mandat/organes/organeRef                  ("PO123456")
    group_acronym        → organe/PO{id}.xml/libelleAbrege           (may be empty)
    group_name           → organe/PO{id}.xml/libelle
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.shared.validators import Legislature, NotBlankStr


class Mandate(BaseModel):
    """
    Represents a single term in the National Assembly.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr
    deputy_uid: NotBlankStr

    legislature: Legislature
    mandate_start: date | None = None
    mandate_end: date | None = None

    group_uid: str | None = None       # "PO845401", from the active GP mandat
    group_acronym: str | None = None
    group_name: str | None = None

    constituency_number: int | None = None
    department_name: str | None = None
    department_number: str | None = None

    seat_number: int | None = None

    @computed_field
    @property
    def is_active(self) -> bool:
        return self.mandate_end is None or self.mandate_end > date.today()
