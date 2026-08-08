"""
Law entity — represents a legislative dossier (the Series in our Netflix metaphor).

Sources:
    ZIP JSON: https://data.assemblee-nationale.fr/static/openData/repository/
                {legislature}/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip
    Portal  : https://data.assemblee-nationale.fr/travaux-parlementaires/dossiers-legislatifs

JSON field mapping (root key: dossierParlementaire):
    dossier_uid    → dossierParlementaire/uid
    legislature    → dossierParlementaire/legislature
    title          → dossierParlementaire/titreDossier/titre
    law_type       → dossierParlementaire/procedureParlementaire/code
    texte_uid      → found by adapter inside actesLegislatifs tree via texteAssocie

    stages         → actesLegislatifs tree (RECURSIVE — see adapter)
                    ⚠️ acteLegislatif is a DICT if 1 acte, a LIST if multiple

    initiateur:
        if acteurs/acteur/acteurRef present → deputy proposer (acteurRef = PA...)
        if null or organe only             → government bill

"""
from enum import Enum
from pydantic import BaseModel, ConfigDict, computed_field
from src.domain.entities.legislative_stage import LegislativeStage
from src.domain.shared.validators import Legislature, NotBlankStr


class LawType(str, Enum):
    """
    procedureParlementaire/code values from real DLR files.
    ⚠️ Complete this enum as more codes are discovered.
    """
    ORDINARY_MEMBER_BILL = "2"   # Proposition de loi ordinaire
    INFORMATION_REPORT = "19"  # Rapport d'information sans mission
    # probably "1" for Projet de loi (government) — to confirm
    OTHER = "0"                  # fallback for unknown codes


class LawStatus(str, Enum):
    IN_PROGRESS = "en cours d'examen"
    ADOPTED = "adopté"
    REJECTED = "rejeté"
    WITHDRAWN = "retiré"


class Law(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    dossier_uid: NotBlankStr
    texte_uid: NotBlankStr | None = None
    legislature: Legislature
    title: NotBlankStr
    law_type: LawType

    # "PA775234" if deputy, None if government/null
    initiateur_uid: str | None = None
    stages: list[LegislativeStage] = []
    closure_status: LawStatus | None = None

    @computed_field
    @property
    def status(self) -> LawStatus:
        if self.closure_status is not None:
            return self.closure_status
        if self.is_promulgated:
            return LawStatus.ADOPTED
        return LawStatus.IN_PROGRESS

    @computed_field
    @property
    def current_stage(self) -> LegislativeStage | None:
        reached = [s for s in self.stages if s.updated_stage_date is not None]
        return reached[-1] if reached else None

    @computed_field
    @property
    def is_promulgated(self) -> bool:
        return any(
            s.code == "PROM" and s.updated_stage_date is not None
            for s in self.stages
        )
