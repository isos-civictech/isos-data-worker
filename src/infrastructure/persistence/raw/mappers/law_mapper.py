"""Entity -> `raw` row. Pure transcription."""

from typing import Any

from src.domain.entities.law import Law
from src.domain.entities.law_texte import LawTexte
from src.domain.entities.legislative_stage import LegislativeStage


def law_row(law: Law) -> dict[str, Any]:
    return {
        "dossier_uid": law.dossier_uid,
        "legislature": law.legislature,
        "title": law.title,
        "senate_url": law.senate_url,
        "procedure_code": law.procedure_code,
        "procedure_label": law.procedure_label,
        "initiator_uids": law.initiator_uids,
        "withdrawn": law.withdrawn,
    }


def law_stage_row(stage: LegislativeStage, *, dossier_uid: str) -> dict[str, Any]:
    return {
        "stage_uid": stage.uid,
        "dossier_uid": dossier_uid,
        "code": stage.code,
        "label": stage.label,
        "organe_ref": stage.organe_ref,
        "position": stage.order,
        "started_at": stage.started_at,
        "examined_at": stage.examined_at,
        "concluded_at": stage.concluded_at,
        "decision": stage.decision,
        "decision_code": stage.decision_code,
        "texte_uid": stage.texte_uid,
        "commission_texte_uid": stage.commission_texte_uid,
        "sitting_refs": stage.sitting_refs,
    }


def law_texte_row(texte: LawTexte) -> dict[str, Any]:
    return {
        "uid": texte.uid,
        "dossier_uid": texte.dossier_uid,
        "legislature": texte.legislature,
        "kind": texte.kind,
        "sub_kind": texte.sub_kind,
        "number": texte.number,
        "title": texte.title,
        "short_title": texte.short_title,
        "deposited_at": texte.deposited_at,
        "author_uids": texte.author_uids,
        "organe_uids": texte.organe_uids,
    }
