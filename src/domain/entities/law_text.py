"""
LawText — one version of a law's text, article by article: as deposited (B),
as adopted by the commission (BTC), as adopted in séance (BTA).

Source: not in open data. The website serves each text by its uid:
    https://www.assemblee-nationale.fr/dyn/docs/{texte_uid}.raw
(Word export as HTML, ~400 KB, semantic classes). Sénat and provisional
(TAP) texts are not served. The uids come from raw.law_texte.

HTML mapping (<p class="…"> in document order):
    assnat4TitreNum / assnat4TitreIntit        title heading and its wording
    assnat5ChapitreNum / assnat5ChapitreIntit  chapter heading
    assnat9ArticleNum                          "Article 1er bis": starts an article
    assnatMentionsousarticle                   "(Supprimé)", "(Non modifié)" under an article
    assnatLoiTexte                             one alinéa of the current article
Anything before the first article (cover, exposé des motifs) is dropped.

Versions of one article are the rows with the same article_ref across the
texts of a dossier; amendments target (texte_uid, article_ref) exactly.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.shared.validators import Legislature, NotBlankStr


class TextKind(StrEnum):
    DEPOSITED = "deposited"  # PRJLANR5L17B2681
    COMMISSION = "commission"  # PRJLANR5L17BTC3046
    ADOPTED = "adopted"  # PRJLANR5L17BTA0326


_KIND_BY_MARK = [("BTC", TextKind.COMMISSION), ("BTA", TextKind.ADOPTED), ("B", TextKind.DEPOSITED)]
_NUMBER = re.compile(r"^Article\s+(.+)$", re.I)


def text_kind(texte_uid: str) -> TextKind | None:
    """The letters before the number: B, BTC or BTA."""
    match = re.search(r"(B|BTC|BTA|TAP)\d+$", texte_uid)
    if not match:
        return None
    return dict(_KIND_BY_MARK).get(match.group(1))


class LawArticle(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    texte_uid: NotBlankStr
    article_ref: NotBlankStr  # "Article 2 bis", as amendments name it
    is_new: bool = False  # "(nouveau)": added by this version
    position: int
    section: str | None = None  # "TITRE II – Dispositions relatives à…"
    content: str | None = None  # alinéas, one per line
    mention: str | None = None  # "Supprimé", "Non modifié", "Pour coordination"

    @computed_field
    @property
    def number(self) -> str | None:
        """'2 bis' from 'Article 2 bis'."""
        match = _NUMBER.match(self.article_ref)
        return match.group(1) if match else None


class LawText(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    texte_uid: NotBlankStr
    dossier_uid: str | None = None
    legislature: Legislature
    source_url: str | None = None
    articles: list[LawArticle] = []

    @computed_field
    @property
    def kind(self) -> TextKind | None:
        return text_kind(self.texte_uid)
