"""HTML fragments from the Assemblée nationale -> plain text."""

import html
import re

_BLOCK_END = re.compile(r"</(p|div|li|h[1-6]|tr)>|<br\s*/?>", re.I)
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"[ \t ]+")


def html_to_text(fragment: str | None) -> str | None:
    """
    '<p>Supprimer&nbsp;cet article.</p><p>Exposé</p>' -> 'Supprimer cet article.\\n\\nExposé'.
    Entities are unescaped once (the XML parser already did the first level).
    """
    if not fragment:
        return None
    text = html.unescape(fragment)
    text = _BLOCK_END.sub("\n", text)
    text = _TAG.sub("", text)
    lines = [_SPACES.sub(" ", line).strip() for line in text.splitlines()]
    return "\n\n".join(line for line in lines if line) or None


def split_names(label: str | None) -> list[str]:
    """'Mme&#160;Dupont, M. Martin et Mme Durand' -> ['Mme Dupont', 'M. Martin', 'Mme Durand']."""
    if not label:
        return []
    text = _SPACES.sub(" ", html.unescape(label))
    return [n.strip() for n in re.split(r",| et ", text) if n.strip()]
