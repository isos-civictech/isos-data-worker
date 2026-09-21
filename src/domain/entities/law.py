"""
Law entity — one legislative dossier ("dossier législatif").

Sources:
    ZIP JSON: {base}/static/openData/repository/{legislature}/loi/dossiers_legislatifs/
              Dossiers_Legislatifs.json.zip
              (~37 MB, json/dossierParlementaire/DLR*.json + json/document/*, ignored)
    Portal  : https://www.assemblee-nationale.fr/dyn/{legislature}/dossiers/{dossier_uid}

JSON field mapping (root key: dossierParlementaire):
    dossier_uid      → uid                              "DLR5L17N53940"
    legislature      → legislature                      "17"
    title            → titreDossier/titre
    senate_url       → titreDossier/senatChemin
    procedure_code   → procedureParlementaire/code      "1" projet, "2" proposition, "19" rapport…
    procedure_label  → procedureParlementaire/libelle
    initiator_uids   → initiateur/acteurs/acteur[]/acteurRef   (dict when single, list otherwise)
    stages           → actesLegislatifs/acteLegislatif[] at depth 1 (see legislative_stage.py)

Not every dossier is a law: résolutions (8, 22), rapports (19), missions
(9, 10) share the same file. `is_law` tells them apart.
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.entities.legislative_stage import PROMULGATION_CODE, LegislativeStage
from src.domain.shared.validators import Legislature, NotBlankStr


class LawType(StrEnum):
    BILL = "bill"  # projet de loi (government)
    PROPOSITION = "proposition"  # proposition de loi (members)


# procedureParlementaire/code -> type. Codes 5 and 7 ("projet OU proposition"
# organique / constitutionnelle) are decided by the title.
PROCEDURE_TYPES: dict[str, LawType | None] = {
    "1": LawType.BILL,  # Projet de loi ordinaire
    "2": LawType.PROPOSITION,  # Proposition de loi ordinaire
    "3": LawType.BILL,  # Projet de loi de finances
    "5": None,  # organique
    "6": LawType.BILL,  # Ratification de traités
    "7": None,  # constitutionnelle
    "21": LawType.BILL,  # Loi de finances rectificative
}


class LawStatus(StrEnum):
    SUBMITTED = "submitted"
    IN_DISCUSSION = "in_discussion"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    PROMULGATED = "promulgated"
    WITHDRAWN = "withdrawn"


class Law(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    dossier_uid: NotBlankStr
    legislature: Legislature
    title: NotBlankStr
    senate_url: str | None = None
    procedure_code: NotBlankStr
    procedure_label: str | None = None
    initiator_uids: list[str] = []
    withdrawn: bool = False  # an AN1-RTRINI / ANLUNI-RTRINI act exists
    stages: list[LegislativeStage] = []
    s3_key: str | None = None

    @computed_field
    @property
    def is_law(self) -> bool:
        return self.procedure_code in PROCEDURE_TYPES

    @computed_field
    @property
    def law_type(self) -> LawType | None:
        if not self.is_law:
            return None
        fixed = PROCEDURE_TYPES[self.procedure_code]
        if fixed is not None:
            return fixed
        return LawType.BILL if self.title.lower().startswith("projet") else LawType.PROPOSITION

    @computed_field
    @property
    def texte_uid(self) -> str | None:
        """Uid of the first deposited text."""
        return next((s.texte_uid for s in self.stages if s.texte_uid), None)

    @computed_field
    @property
    def deposited_at(self) -> date | None:
        return next((s.started_at for s in self.stages if s.started_at), None)

    @computed_field
    @property
    def is_promulgated(self) -> bool:
        return any(s.code == PROMULGATION_CODE and s.concluded_at for s in self.stages)

    @computed_field
    @property
    def status(self) -> LawStatus:
        if self.is_promulgated:
            return LawStatus.PROMULGATED
        if self.withdrawn:
            return LawStatus.WITHDRAWN
        decided = [s for s in self.stages if s.is_reading and s.decision_code]
        if decided and decided[-1].rejected:
            return LawStatus.REJECTED
        if decided and decided[-1].code == "ANLDEF":
            return LawStatus.ADOPTED
        if any(s.examined_at for s in self.stages):
            return LawStatus.IN_DISCUSSION
        return LawStatus.SUBMITTED
