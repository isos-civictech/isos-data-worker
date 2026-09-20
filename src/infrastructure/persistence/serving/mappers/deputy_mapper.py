"""
`raw` row -> `public` row. This is where adaptation happens: slug, official
page URL, integer FKs, fields the display schema lacks (gender, profession)
are dropped.
"""

from typing import Any

from sqlalchemy.engine import RowMapping

from src.infrastructure.persistence.serving.slug import deputy_slug

DEPUTY_PAGE = "https://www.assemblee-nationale.fr/dyn/deputes/{uid}"


def political_group_row(raw: RowMapping, *, legislature_id: int) -> dict[str, Any]:
    return {
        "legislature_id": legislature_id,
        "name": raw["name"][:255],
        "short_name": raw["short_name"],
        "external_id": raw["uid"],
    }


def deputy_row(raw: RowMapping, mandate: RowMapping | None) -> dict[str, Any]:
    return {
        "first_name": raw["first_name"][:255],
        "last_name": raw["last_name"][:255],
        "slug": deputy_slug(raw["first_name"], raw["last_name"]),
        "picture": raw["photo_url"],
        "birth_date": raw["birth_date"],
        "constituency": str(mandate["constituency_number"])
        if mandate and mandate["constituency_number"] is not None
        else None,
        "department": mandate["department_name"] if mandate else None,
        "external_id": raw["uid"],
        "source_url": DEPUTY_PAGE.format(uid=raw["uid"]),
    }


def mandate_row(
    raw: RowMapping, *, deputy_id: int, legislature_id: int, political_group_id: int
) -> dict[str, Any]:
    return {
        "deputy_id": deputy_id,
        "legislature_id": legislature_id,
        "political_group_id": political_group_id,
        "started_at": raw["mandate_start"],
        "ended_at": raw["mandate_end"],
    }
