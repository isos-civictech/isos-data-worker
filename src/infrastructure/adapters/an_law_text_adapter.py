"""
Law text adapter — the articles of a text, scraped from the website.

Source: https://www.assemblee-nationale.fr/dyn/docs/{texte_uid}.raw
The HTML is archived as is in S3 (raw/law_texts/{legislature}/{uid}.html):
if the markup changes one day, only this parser needs to catch up.
"""

import re

import httpx
from lxml import html

from src.domain.entities.law_text import LawArticle, LawText
from src.domain.ports.sources.law_text_source import LawTextSource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.http.client import HttpClient

DOC_URL = "https://www.assemblee-nationale.fr/dyn/docs/{uid}.raw"

ARTICLE = "assnat9ArticleNum"
MENTION = "assnatMentionsousarticle"
HEADINGS = {  # class -> (level, is the number part)
    "assnat4TitreNum": ("title", True),
    "assnat4TitreIntit": ("title", False),
    "assnat5ChapitreNum": ("chapter", True),
    "assnat5ChapitreIntit": ("chapter", False),
}
_SPACES = re.compile(r"[ \t\u00a0]+")
_NEW = re.compile(r"\s*\((nouveau|nouvelle)\)\s*$", re.I)


def _clean(node) -> str:
    text = node.text_content()
    text = text.replace("‑", "-")  # non-breaking hyphen
    return _SPACES.sub(" ", text).strip()


class AnLawTextAdapter(LawTextSource):
    def __init__(self, http: HttpClient, storage: RawStoragePort) -> None:
        self._http = http
        self._storage = storage
        self.last_s3_key: str | None = None

    async def fetch(self, texte_uid: str, legislature: Legislature) -> LawText | None:
        url = DOC_URL.format(uid=texte_uid)
        try:
            payload = await self._http.get_bytes(url)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise
        self.last_s3_key = await self._storage.put(
            f"raw/law_texts/{legislature}/{texte_uid}.html", payload, content_type="text/html"
        )
        law_text = self._parse(payload, texte_uid, legislature)
        law_text.source_url = url
        return law_text

    # -- parsing: pure function, covered by tests/adapters ----------------------

    @staticmethod
    def _parse(payload: bytes, texte_uid: str, legislature: int) -> LawText:
        root = html.fromstring(payload.decode("utf-8", errors="replace"))
        articles: list[LawArticle] = []
        section: dict[str, str] = {}  # "title" / "chapter" -> heading
        current: LawArticle | None = None
        alineas: list[str] = []

        def close() -> None:
            if current is not None:
                current.content = "\n".join(alineas) or None
                articles.append(current)

        for p in root.iter("p"):
            css = p.get("class") or ""
            text = _clean(p)
            if css == ARTICLE:
                close()
                if not text:
                    current = None  # an empty heading (page furniture), not an article
                    continue
                current = LawArticle(
                    texte_uid=texte_uid,
                    # "Article 2 bis (nouveau)": amendments say "Article 2 bis".
                    article_ref=_NEW.sub("", text),
                    is_new=bool(_NEW.search(text)),
                    position=len(articles) + 1,
                    section=" – ".join(
                        v for v in (section.get("title"), section.get("chapter")) if v
                    )
                    or None,
                )
                alineas = []
            elif css in HEADINGS:
                level, is_number = HEADINGS[css]
                if is_number:
                    section[level] = text
                    if level == "title":
                        section.pop("chapter", None)
                elif text and level in section:
                    section[level] = f"{section[level]} – {text}"
            elif current is not None and css == MENTION:
                current.mention = text.strip("()") or None
            elif current is not None and text:
                alineas.append(text)
        close()
        return LawText(texte_uid=texte_uid, legislature=legislature, articles=articles)
