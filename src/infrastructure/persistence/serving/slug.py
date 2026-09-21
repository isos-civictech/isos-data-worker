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


async def unique_slug(connection, table, slug: str, external_id: str) -> str:
    """Append the uid when another row already owns this slug (homonyms, rescheduled sittings)."""
    import sqlalchemy as sa

    taken_by_other = await connection.execute(
        sa.select(table.c.id).where(table.c.slug == slug, table.c.external_id != external_id)
    )
    return f"{slug}-{slugify(external_id)}" if taken_by_other.scalar() else slug
