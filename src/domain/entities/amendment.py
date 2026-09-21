"""
Amendment — a proposed change to one division of a legislative text.

Source: {base}/static/openData/repository/{legislature}/loi/amendements_div_legis/
        Amendements.xml.zip
        (~340 MB, ~125 000 files: xml/{dossier_uid}/{texte_uid}/{uid}.xml)

XML field mapping (root: amendement, default namespace):
    uid              → uid                               "AMANR5L17PO838901B2681P0D1N000225"
    legislature      → legislature
    dossier_uid      → from the archive path             "DLR5L17N53940"
    texte_uid        → texteLegislatifRef                "PRJLANR5L17B2681"
    examen_ref       → examenRef                         "EXANR5L17PO838901B2681P0D1"
    number           → identification/numeroLong        "225", "II-CF146", "CL12" (not an int)
    rectification    → identification/numeroRect         0 = original, 1 = "rect.", 2 = "2e rect."
    examined_by      → identification/prefixeOrganeExamen  "AN" = séance publique, else a commission
    parent_uid       → amendementParentRef               set on a sous-amendement
    author_type      → signataires/auteur/typeAuteur      Député | Rapporteur | Gouvernement
    deputy_uid       → signataires/auteur/acteurRef
    group_uid        → signataires/auteur/groupePolitiqueRef
    cosigner_uids    → signataires/cosignataires/acteurRef[]
    signatories      → signataires/libelle                names, split on ',' and 'et'
    division_title   → pointeurFragmentTexte/division/titre     "Article 2"
    division_type    → …/division/type                      ARTICLE | ANNEXE | TITRE | CHAPITRE
    division_position→ …/division/avant_A_Apres             Avant | A | Après
    alinea           → …/amendementStandard/alinea/alineaDesignation  "Après l'alinéa 34"
    content          → corps/contenuAuteur/dispositif      HTML in the source, plain text here
    summary          → corps/contenuAuteur/exposeSommaire  idem ("exposé sommaire")
    deposited_at     → cycleDeVie/dateDepot
    published_at     → cycleDeVie/datePublication
    state            → cycleDeVie/etatDesTraitements/etat/libelle   "Discuté", "Irrecevable 40"…
    sub_state        → cycleDeVie/etatDesTraitements/sousEtat/libelle
    sort             → cycleDeVie/sort           Adopté | Rejeté | Tombé | Retiré | Non soutenu
    sorted_at        → cycleDeVie/dateSort
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.shared.validators import Legislature, NotBlankStr

PUBLIC_SITTING = "AN"


class AmendmentAuthorType(StrEnum):
    DEPUTY = "Député"
    RAPPORTEUR = "Rapporteur"
    GOVERNMENT = "Gouvernement"


class AmendmentStatus(StrEnum):
    ADOPTED = "adopted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    FALLEN = "fallen"  # "Tombé": moot after another decision
    INADMISSIBLE = "inadmissible"
    UNSUPPORTED = "unsupported"  # "Non soutenu": author absent
    PENDING = "pending"


SORT_STATUS = {
    "Adopté": AmendmentStatus.ADOPTED,
    "Rejeté": AmendmentStatus.REJECTED,
    "Retiré": AmendmentStatus.WITHDRAWN,
    "Tombé": AmendmentStatus.FALLEN,
    "Non soutenu": AmendmentStatus.UNSUPPORTED,
    "Irrecevable": AmendmentStatus.INADMISSIBLE,
}


class Amendment(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    uid: NotBlankStr
    legislature: Legislature
    dossier_uid: str | None = None
    texte_uid: NotBlankStr
    examen_ref: str | None = None
    number: str | None = None
    rectification: int = 0
    examined_by: str | None = None
    parent_uid: str | None = None
    author_type: AmendmentAuthorType
    deputy_uid: str | None = None
    group_uid: str | None = None
    cosigner_uids: list[str] = []
    signatories: list[str] = []
    division_title: str | None = None
    division_type: str | None = None
    division_position: str | None = None
    alinea: str | None = None
    content: str | None = None
    summary: str | None = None
    deposited_at: date | None = None
    published_at: date | None = None
    state: str | None = None
    sub_state: str | None = None
    sort: str | None = None
    sorted_at: datetime | None = None

    @computed_field
    @property
    def in_public_sitting(self) -> bool:
        return self.examined_by == PUBLIC_SITTING

    @computed_field
    @property
    def article_ref(self) -> str | None:
        """'Après l'article 5', 'Article 2', 'Avant l'article 1er' — one display string."""
        if not self.division_title:
            return None
        if self.division_position in ("Avant", "Après"):
            title = self.division_title
            title = title[0].lower() + title[1:] if title[:1].isupper() else title
            return f"{self.division_position} l'{title}"
        return self.division_title

    @computed_field
    @property
    def status(self) -> AmendmentStatus:
        if self.sort in SORT_STATUS:
            return SORT_STATUS[self.sort]
        if self.state and self.state.startswith("Irrecevable"):
            return AmendmentStatus.INADMISSIBLE
        if self.state == "Retiré":
            return AmendmentStatus.WITHDRAWN
        return AmendmentStatus.PENDING
