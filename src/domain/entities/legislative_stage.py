"""
LegislativeStage entity — one step in the parliamentary shuttle.

Source: inside Dossiers_Legislatifs.json.zip
JSON path: dossierLegislatif/actesLegislatifs[]/
    code    → codeActe
    label   → libelleActe/nomLong
    updated_stage_date    → dateActe  (null = not yet reached)

Known stage codes (non-exhaustive list):
    AN1-DEPOT  → Dépôt à l'Assemblée nationale
    AN1-COM    → Examen en commission (AN)
    AN1-VOTE   → Vote en 1ère lecture (AN)
    SN1-DEPOT  → Transmis au Sénat
    SN1-COM    → Examen en commission (Sénat)
    SN1-VOTE   → Vote en 1ère lecture (Sénat)
    AN2-VOTE   → Vote en 2ème lecture (AN)
    SN2-VOTE   → Vote en 2ème lecture (Sénat)
    CMP        → Commission mixte paritaire
    CC         → Conseil Constitutionnel
    PROM       → Promulgation
"""
from datetime import date
from pydantic import BaseModel
from src.domain.shared.validators import NotBlankStr


class LegislativeStage(BaseModel):

    code: NotBlankStr
    label: NotBlankStr
    updated_stage_date: date | None = None

    class Config:
        from_attributes = True