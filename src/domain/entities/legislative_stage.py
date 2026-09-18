"""
LegislativeStage entity — one step in the parliamentary shuttle.

Known stage codes (non-exhaustive list):
    SN1-DEPOT           → 1er dépôt d'une initiative (Sénat)
    SN1-COM             → Travaux des commissions (Sénat)
    SN1-COM-FOND        → Travaux de la commission saisie au fond
    SN1-COM-FOND-SAISIE → Renvoi en commission au fond
    AN20-RAPPORT        → Dépôt de rapport
    PROM                → Promulgation
"""
from datetime import date

from pydantic import BaseModel, ConfigDict

from src.domain.shared.validators import NotBlankStr


class LegislativeStage(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    code: NotBlankStr
    label: NotBlankStr
    updated_stage_date: date | None = None
