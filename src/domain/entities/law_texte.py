"""
LawTexte — one document attached to a dossier: the deposited text, the
commission's text, a report… Metadata only; the body is not in open data.

Source: json/document/*.json in Dossiers_Legislatifs.json.zip (see law.py)

JSON field mapping (root key: document):
    uid              → uid              "PRJLANR5L17B2681" (B = deposited, BTC = commission text)
    dossier_uid      → dossierRef
    legislature      → legislature
    kind             → classification/type/code       PRJL | PION | PNRE | RAPP | RINF | AVIS…
    sub_kind         → classification/sousType/code   ORG, CONST, AUTRATCONV…
    number           → notice/numNotice               2681 — the "n° 2681" everyone quotes
    title            → titres/titrePrincipal
    short_title      → titres/titrePrincipalCourt
    deposited_at     → cycleDeVie/chrono/dateDepot
    author_uids      → auteurs/auteur[]/acteur/acteurRef
    organe_uids      → auteurs/auteur[]/organe/organeRef
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.shared.validators import Legislature, NotBlankStr

LAW_TEXT_KINDS = {"PRJL", "PION"}


class LawTexte(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    uid: NotBlankStr
    dossier_uid: NotBlankStr
    legislature: Legislature
    kind: str | None = None
    sub_kind: str | None = None
    number: int | None = None
    title: str | None = None
    short_title: str | None = None
    deposited_at: date | None = None
    author_uids: list[str] = []
    organe_uids: list[str] = []

    @computed_field
    @property
    def is_law_text(self) -> bool:
        """A projet or proposition de loi, as opposed to a report or an opinion."""
        return self.kind in LAW_TEXT_KINDS

    @computed_field
    @property
    def is_assemblee(self) -> bool:
        """PRJL*AN*R5… was deposited at the Assemblée, PRJL*SN*R5… at the Sénat."""
        return self.uid[4:6] == "AN"

    @computed_field
    @property
    def is_commission_text(self) -> bool:
        return "BTC" in self.uid
