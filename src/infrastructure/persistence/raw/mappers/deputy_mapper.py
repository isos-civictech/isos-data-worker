"""
Entity → `raw` row. Pure transcription: no slug, no enum translation, no FK
resolution. Fields the display schema lacks (gender, profession) are kept.
"""
from typing import Any

from src.domain.entities.deputy import Deputy
from src.domain.entities.mandate import Mandate
from src.domain.entities.political_group import PoliticalGroupRef


def political_group_row(group: PoliticalGroupRef) -> dict[str, Any]:
    return {
        "uid": group.uid,
        "legislature": group.legislature,
        "name": group.name,
        "short_name": group.short_name,
    }


def deputy_row(deputy: Deputy, *, legislature: int) -> dict[str, Any]:
    return {
        "uid": deputy.uid,
        "legislature": legislature,
        "first_name": deputy.first_name,
        "last_name": deputy.last_name,
        "birth_date": deputy.birth_date,
        "gender": deputy.gender,
        "profession": deputy.profession,
        # HttpUrl is not a str for asyncpg.
        "photo_url": str(deputy.photo_url) if deputy.photo_url else None,
    }


def mandate_row(mandate: Mandate) -> dict[str, Any]:
    return {
        "uid": mandate.uid,
        "deputy_uid": mandate.deputy_uid,
        "legislature": mandate.legislature,
        "mandate_start": mandate.mandate_start,
        "mandate_end": mandate.mandate_end,
        "group_uid": mandate.group_uid,
        "constituency_number": mandate.constituency_number,
        "department_name": mandate.department_name,
        "department_number": mandate.department_number,
        "seat_number": mandate.seat_number,
    }
