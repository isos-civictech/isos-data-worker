"""URL slugs for the display schema (stdlib only)."""

import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_length: int = 200) -> str:
    """'Jean-Luc Mélenchon' -> 'jean-luc-melenchon'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _NON_ALNUM.sub("-", ascii_text.lower()).strip("-")
    return slug[:max_length].rstrip("-")


def deputy_slug(first_name: str, last_name: str) -> str:
    return slugify(f"{first_name} {last_name}")
