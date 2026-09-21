"""`raw.amendment` row -> `public.amendment` row."""

from typing import Any

from src.domain.entities.amendment import Amendment

# Public enum has deputy | group | government | commission. A rapporteur
# amends on behalf of the commission.
AUTHOR_TYPES = {"Député": "deputy", "Rapporteur": "commission", "Gouvernement": "government"}


def amendment_from_raw(row: dict[str, Any]) -> Amendment:
    return Amendment(**{k: row[k] for k in Amendment.model_fields if k in row})


def amendment_row(
    a: Amendment,
    *,
    law_id: int,
    deputy_id: int | None,
    group_id: int | None,
    reading_id: int | None,
) -> dict[str, Any]:
    return {
        "law_id": law_id,
        "debate_id": None,  # an amendment is not tied to one sitting in the source
        "law_reading_id": reading_id,
        "number": a.number,
        "examined_by": a.examined_by,
        "article_ref": (a.article_ref or "")[:255] or None,
        "author_type": AUTHOR_TYPES[a.author_type.value],
        "deputy_id": deputy_id,
        "political_group_id": group_id,
        "content": a.content,
        "summary": a.summary,
        "status": a.status.value,
        "deposited_at": a.deposited_at,
        "external_id": a.uid,
    }
