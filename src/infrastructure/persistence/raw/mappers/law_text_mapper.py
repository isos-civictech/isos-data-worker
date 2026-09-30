"""Entity -> `raw` row. Pure transcription."""

from typing import Any

from src.domain.entities.law_text import LawArticle, LawText


def law_text_row(t: LawText) -> dict[str, Any]:
    return {
        "texte_uid": t.texte_uid,
        "dossier_uid": t.dossier_uid,
        "legislature": t.legislature,
        "kind": t.kind.value if t.kind else None,
        "available": True,
        "source_url": t.source_url,
        "article_count": len(t.articles),
    }


def law_article_row(a: LawArticle) -> dict[str, Any]:
    return {
        "texte_uid": a.texte_uid,
        "article_ref": a.article_ref,
        "is_new": a.is_new,
        "position": a.position,
        "section": a.section,
        "content": a.content,
        "mention": a.mention,
    }
