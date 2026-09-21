"""Entity -> `raw` row. Pure transcription."""

from typing import Any

from src.domain.entities.amendment import Amendment


def amendment_row(a: Amendment) -> dict[str, Any]:
    return {
        "uid": a.uid,
        "legislature": a.legislature,
        "dossier_uid": a.dossier_uid,
        "texte_uid": a.texte_uid,
        "examen_ref": a.examen_ref,
        "number": a.number,
        "rectification": a.rectification,
        "examined_in": a.examined_by,
        "parent_uid": a.parent_uid,
        "author_type": a.author_type.value,
        "deputy_uid": a.deputy_uid,
        "group_uid": a.group_uid,
        "cosigner_uids": a.cosigner_uids,
        "signatories": a.signatories,
        "division_title": a.division_title,
        "division_type": a.division_type,
        "division_position": a.division_position,
        "alinea": a.alinea,
        "content": a.content,
        "summary": a.summary,
        "deposited_at": a.deposited_at,
        "published_at": a.published_at,
        "state": a.state,
        "sub_state": a.sub_state,
        "sort": a.sort,
        "sorted_at": a.sorted_at,
    }
