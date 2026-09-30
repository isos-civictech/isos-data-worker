from datetime import date

from pydantic import BaseModel, ConfigDict, HttpUrl, computed_field

from src.domain.entities.government_role import GovernmentRole
from src.domain.entities.mandate import Mandate
from src.domain.shared.validators import NotBlankStr


class Deputy(BaseModel):
    """
    A person with a seat at the Assemblée during the legislature, or a member
    of the government during it (ministers speak and amend too).

    Source: AMO30 — every actor, mandate and organe of the legislature, past and present.
        zip(xml) : {base}/static/openData/repository/{legislature}/amo/
                   tous_acteurs_mandats_organes_xi_legislature/
                   AMO30_tous_acteurs_tous_mandats_tous_organes_historique.xml.zip
        portal   : https://data.assemblee-nationale.fr/acteurs/historique-des-deputes

    XML field mapping (acteur/PA{id}.xml in ZIP):
        uid                  → acteur/uid
        first_name           → acteur/etatCivil/ident/prenom
        last_name            → acteur/etatCivil/ident/nom
        birth_date           → acteur/etatCivil/infoNaissance/dateNais
        gender               → acteur/etatCivil/ident/civ          "M." | "Mme"
        profession           → acteur/profession/libelleCourant
        photo_url            → derived from the uid (official portrait)
        mandates             → every ASSEMBLEE mandat of the legislature (see mandate.py)
        government_roles     → every MINISTERE post overlapping it (see government_role.py)
    """

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr

    first_name: NotBlankStr
    last_name: NotBlankStr
    birth_date: date | None = None
    gender: str | None = None  # "M" or "F" or None
    profession: str | None = None

    photo_url: HttpUrl | None = None

    mandates: list[Mandate] = []
    government_roles: list[GovernmentRole] = []

    @computed_field
    @property
    def is_deputy(self) -> bool:
        """Held a seat during the legislature; a minister who never sat is not one."""
        return bool(self.mandates)

    @computed_field
    @property
    def is_minister(self) -> bool:
        return bool(self.government_roles)
