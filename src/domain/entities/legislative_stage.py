"""
LegislativeStage — one top-level phase of a dossier's parliamentary journey.

Source: `actesLegislatifs/acteLegislatif` at depth 1 of a dossier
(see law.py). Each top-level acte is a phase (a reading in one chamber, the
CMP, the Conseil constitutionnel, the promulgation) and nests the detailed
acts (dépôt, commission, séance, décision) underneath it.

JSON field mapping (one depth-1 acteLegislatif):
    uid           → uid                          "DLR5L17N53940-AN1"
    code          → codeActe                     "AN1", "SN1", "CMP", "CC", "PROM", "AN20"…
    label         → libelleActe/nomCanonique     "1ère lecture (2ème assemblée saisie)"
    organe_ref    → organeRef                    "PO838901" (AN), "PO78718" (Sénat)
    order         → position in the list
    Derived from the nested acts (any depth):
    started_at    → earliest dateActe (usually the dépôt)
    examined_at   → earliest dateActe of a *-REUNION, *-RAPPORT, *-SEANCE or *-DEC act:
                    the moment the chamber actually starts working on the text
    concluded_at  → dateActe of the *-DEC / PROM-PUB act
    decision      → statutConclusion/libelle of that act   "adopté", "rejeté", "modifié"
    decision_code → statutConclusion/fam_code               "TSORTF01", "TSORTF07"…
    texte_uid     → texteAssocie of the *-DEPOT act         "PRJLANR5L17B2681"
    commission_texte_uid → texteAdopte of the *-COM-FOND-RAPPORT act  "PRJLANR5L17BTC3046"
                    (séance amendments target this one, commission amendments the deposited one)
    sitting_refs  → reunionRef of *-DEBATS-SEANCE acts      "RUANR5L17S2026IDS30781"
                    (= agenda uid = public.debate.external_id)
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.shared.validators import NotBlankStr

# Stage codes that are a reading of a text (public.law_reading); the rest
# (CC, PROM, AN20 "travaux", AN21 motion de censure…) are not.
READING_CODES = {
    "AN1", "AN2", "ANNLEC", "ANLDEF", "ANLUNI",
    "SN1", "SN2", "SNNLEC", "SNLDEF", "SNLUNI",
    "CMP",
}  # fmt: skip

REJECTED_CODES = {"TSORTF07", "TMRC01"}
PROMULGATION_CODE = "PROM"


class LegislativeStage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    uid: NotBlankStr
    code: NotBlankStr
    label: NotBlankStr
    organe_ref: str | None = None
    order: int = 0
    started_at: date | None = None
    examined_at: date | None = None
    concluded_at: date | None = None
    decision: str | None = None
    decision_code: str | None = None
    texte_uid: str | None = None
    commission_texte_uid: str | None = None
    sitting_refs: list[str] = []

    @computed_field
    @property
    def is_reading(self) -> bool:
        return self.code in READING_CODES

    @computed_field
    @property
    def rejected(self) -> bool:
        return self.decision_code in REJECTED_CODES
