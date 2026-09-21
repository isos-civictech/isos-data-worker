"""Entity -> `raw` row. Pure transcription."""

from typing import Any

from src.domain.entities.ballot import Ballot, BallotVote, GroupVote


def ballot_row(b: Ballot) -> dict[str, Any]:
    return {
        "uid": b.uid,
        "legislature": b.legislature,
        "number": b.number,
        "sitting_uid": b.sitting_uid,
        "session_ref": b.session_ref,
        "date": b.date,
        "kind": b.kind.value,
        "kind_label": b.kind_label,
        "majority_rule": b.majority_rule,
        "result": b.result,
        "title": b.title,
        "requested_by": b.requested_by,
        "dossier_uid": b.dossier_uid,
        "location": b.location,
        "voters": b.voters,
        "expressed": b.expressed,
        "required": b.required,
        "for_count": b.for_count,
        "against_count": b.against_count,
        "abstention_count": b.abstention_count,
        "non_voting_count": b.non_voting_count,
        "non_voting_voluntary_count": b.non_voting_voluntary_count,
    }


def ballot_group_row(g: GroupVote, *, ballot_uid: str) -> dict[str, Any]:
    return {
        "ballot_uid": ballot_uid,
        "group_uid": g.group_uid,
        "members": g.members,
        "majority_position": g.majority_position,
        "for_count": g.for_count,
        "against_count": g.against_count,
        "abstention_count": g.abstention_count,
        "non_voting_count": g.non_voting_count,
    }


def ballot_vote_row(v: BallotVote, *, ballot_uid: str) -> dict[str, Any]:
    return {
        "ballot_uid": ballot_uid,
        "deputy_uid": v.deputy_uid,
        "mandate_uid": v.mandate_uid,
        "group_uid": v.group_uid,
        "position": v.position.value,
        "by_delegation": v.by_delegation,
        "corrected_position": v.corrected_position.value if v.corrected_position else None,
    }
