"""
LawArticle — a versioned snapshot of one article of a Law.

Source: HTML pages (NOT in ZIP files)
    URL: https://www.assemblee-nationale.fr/dyn/{legislature}/textes/{texte_uid}

S3 path: raw/law_articles/{legislature}/{texte_uid}/{article_ref}_{version}.html
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from src.domain.shared.validators import Legislature, NotBlankStr

class ArticleVersion(str, Enum):
    ORIGINAL = "original"
    PRE_AMENDMENT = "pre_amendment"
    POST_AMENDMENT = "post_amendment"


class LawArticle(BaseModel):
    texte_uid: NotBlankStr
    article_ref: NotBlankStr
    article_number: int | None = None
    legislature: Legislature
    content: NotBlankStr
    version: ArticleVersion
    amendment_uid: str | None = None
    scraped_at: datetime

    # ── S3 ────────────────────────────────────────────────────────────────────
    s3_key: str | None = None

    class Config:
        from_attributes = True