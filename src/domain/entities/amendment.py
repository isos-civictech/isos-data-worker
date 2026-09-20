"""
Amendment — a proposed modification to one article of a Law.

Source: Amendements XML
    ZIP: https://data.assemblee-nationale.fr/static/openData/repository/
        {legislature}/loi/amendements_legislatifs/Amendements_XVII.xml.zip
    Single file: https://www.assemblee-nationale.fr/dyn/opendata/{uid}.xml

XML field mapping:
    uid            → amendement/uid
    legislature    → derived from uid pattern or file context
    texte_uid      → amendement/texteLegislatifRef
    article_ref    → amendement/pointeurArticle/articleDesigne/alineaDesigne/titreArticle
    deputy_uid     → amendement/auteur/acteurRef
    author_type    → derived: acteurRef present = deputy, organe = government/commission
    content        → amendement/corps/texteAmendement
    expose_motifs  → amendement/exposeSommaire
    sort           → amendement/sortAmendement/libelleFR

S3 path: raw/amendments/{legislature}/{texte_uid}/{uid}.xml
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from src.domain.shared.validators import Legislature, NotBlankStr


class AmendmentAuthorType(StrEnum):
    DEPUTY = "Député"
    GROUP = "Groupe"
    GOVERNMENT = "Gouvernement"
    COMMISSION = "Commission"


class AmendmentSort(StrEnum):
    ADOPTED = "Adopté"
    REJECTED = "Rejeté"
    WITHDRAWN = "Retiré"
    LAPSED = "Tombé"
    INADMISSIBLE = "Irrecevable"
    UNSUPPORTED = "Non soutenu"
    UNREPORTED = "Non renseigné"
    PENDING = "En attente"


class Amendment(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr
    legislature: Legislature
    texte_uid: NotBlankStr
    article_ref: str | None = None
    deputy_uid: str | None = None
    debate_uid: str | None = None
    author_type: AmendmentAuthorType
    author_name: str | None = None
    content: str | None = None
    expose_motifs: str | None = None
    sort: AmendmentSort = AmendmentSort.PENDING

    # ── S3 ────────────────────────────────────────────────────────────────────
    s3_key: str | None = None
