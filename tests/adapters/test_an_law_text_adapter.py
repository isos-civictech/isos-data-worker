"""Parsing tests against a real text page (commission text, trimmed to five articles)."""

from pathlib import Path

import pytest

from src.domain.entities.law_text import TextKind, text_kind
from src.infrastructure.adapters.an_law_text_adapter import AnLawTextAdapter

FIXTURE = Path(__file__).parent.parent / "fixtures" / "an" / "texte_PRJLANR5L17BTC3046.html"


@pytest.fixture
def law_text():
    return AnLawTextAdapter._parse(FIXTURE.read_bytes(), "PRJLANR5L17BTC3046", 17)


def test_kind_from_uid():
    assert text_kind("PRJLANR5L17B2681") == TextKind.DEPOSITED
    assert text_kind("PRJLANR5L17BTC3046") == TextKind.COMMISSION
    assert text_kind("PIONANR5L17BTA0097") == TextKind.ADOPTED
    assert text_kind("PRJLANR5L17TAP0326") is None, "provisional texts are not served"


def test_articles_in_order(law_text):
    assert law_text.kind == TextKind.COMMISSION
    assert [a.article_ref for a in law_text.articles] == [
        "Article 1er",
        "Article 1er bis",
        "Article 2",
        "Article 2 bis",
        "Article 3",
    ]
    assert [a.position for a in law_text.articles] == [1, 2, 3, 4, 5]
    assert law_text.articles[2].number == "2"


def test_article_content_and_section(law_text):
    first = law_text.articles[0]
    assert first.section.startswith("TITRE Ier – DISPOSITIONS TENDANT")
    assert first.content.startswith("I. – Le code de procédure pénale est ainsi modifié :\n")
    assert "‑" not in first.content, "non-breaking hyphens are normalised"
    assert "<" not in first.content


def test_new_article_marker():
    html = (
        b'<html><body><p class="assnat9ArticleNum">Article 2 bis (nouveau)</p>'
        b'<p class="assnatLoiTexte">Texte.</p></body></html>'
    )
    (added,) = AnLawTextAdapter._parse(html, "PIONANR5L17BTA0001", 17).articles
    assert added.article_ref == "Article 2 bis", "'(nouveau)' is not part of the ref"
    assert added.is_new and added.content == "Texte."
