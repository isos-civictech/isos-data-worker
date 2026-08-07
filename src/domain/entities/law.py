"""
Law entity — represents a legislative dossier (the Series in our Netflix metaphor).

Sources:
    ZIP JSON : https://data.assemblee-nationale.fr/static/openData/repository/
                17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip
    ZIP XML  : https://data.assemblee-nationale.fr/static/openData/repository/
                17/loi/dossiers_legislatifs/Dossiers_Legislatifs.xml.zip
    Portal   : https://data.assemblee-nationale.fr/travaux-parlementaires/dossiers-legislatifs

JSON field mapping:
    dossier_uid    → dossierLegislatif/uid
    texte_uid      → dossierLegislatif/textes[0]/uid
    legislature    → dossierLegislatif/legislature
    title          → dossierLegislatif/titrePrincipal
    law_type       → dossierLegislatif/textes[0]/type  ("PRJL" or "PION")
    themes         → dossierLegislatif/themes[]
    stages         → dossierLegislatif/actesLegislatifs[]
    status         → derived from stages — see is_promulgated, current_stage
"""
from enum import Enum
from pydantic import BaseModel, computed_field
from src.domain.entities.legislative_stage import LegislativeStage
from src.domain.shared.validators import Legislature, NotBlankStr


class LawType(str, Enum):
    """
    Origin of the law.
    PRJL = Projet de loi — comes from the government.
    PION = Proposition de loi — comes from a deputy.
    """
    GOVERNMENT_BILL = "PRJL"
    MEMBER_BILL = "PION"
    OTHER = "OTHER"


class LawStatus(str, Enum):
    """
    Current status of the law.
    """
    IN_PROGRESS = "en cours d'examen"
    ADOPTED = "adopté"
    REJECTED = "rejeté"
    WITHDRAWN = "retiré"


class Law(BaseModel):
    dossier_uid: NotBlankStr
    texte_uid: NotBlankStr
    legislature: Legislature
    title: NotBlankStr
    law_type: LawType
    themes: list[str] = []
    status: LawStatus = LawStatus.IN_PROGRESS
    stages: list[LegislativeStage] = []

    @computed_field
    @property
    def current_stage(self) -> LegislativeStage | None:
        """
        The most recent stage that has been reached (date is not None).
        """
        reached = [s for s in self.stages if s.updated_stage_date is not None]
        return reached[-1] if reached else None

    @computed_field
    @property
    def is_promulgated(self) -> bool:
        """
        True if the law has reached the PROM (promulgation) stage.
        """
        return any(s.code == "PROM" and s.updated_stage_date is not None for s in self.stages)

    class Config:
        from_attributes = True