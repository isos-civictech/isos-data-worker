from datetime import date
from domain.entities.mandate import Mandate
from domain.shared.validators import NotBlankStr
from pydantic import BaseModel, HttpUrl

class Deputy(BaseModel):
    """
    Represents a person who holds or held a mandate.
    
    URLS : {
        zip(xml) : https://data.assemblee-nationale.fr/static/openData/repository/17/amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.xml.zip,
        portal : https://data.assemblee-nationale.fr/acteurs/deputes-en-exercice}
        Single deputy:
            - https://www.assemblee-nationale.fr/dyn/opendata/{uid}.xml
            - https://www.nosdeputes.fr/{first_name}-{last_name}/json

    XML field mapping (acteur/PA{id}.xml in ZIP):
        uid                  → acteur/uid
        first_name           → acteur/etatCivil/ident/prenom
        last_name            → acteur/etatCivil/ident/nom
        birth_date           → acteur/etatCivil/ident/dateNais
        gender               → acteur/etatCivil/ident/sexe
        photo_url            → https://www.nosdeputes.fr/depute/photo/{slug}/150.   slug = slug = f"{first_name}-{last_name}".lower().replace(" ", "-")
    """

    uid: NotBlankStr

    first_name: NotBlankStr
    last_name: NotBlankStr
    birth_date: date | None = None
    gender: str | None = None           # "M" or "F"
    profession: str | None = None

    photo_url: HttpUrl | None = None
    
    mandates: list[Mandate] = []
    class Config:
        from_attributes = True
