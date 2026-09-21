"""Parsing tests against a real scrutin file, trimmed to two groups."""

from datetime import date
from pathlib import Path

import pytest

from src.domain.entities.ballot import BallotKind, VotePosition
from src.infrastructure.adapters.an_ballot_adapter import AnBallotAdapter

FIXTURE = Path(__file__).parent.parent / "fixtures" / "an" / "scrutin_VTANR5L17V3985.json"


@pytest.fixture
def ballot():
    return AnBallotAdapter._parse(FIXTURE.read_bytes())


def test_header(ballot):
    assert ballot.uid == "VTANR5L17V3985"
    assert ballot.number == 3985
    assert ballot.sitting_uid == "RUANR5L17S2026IDS29933", "the agenda uid: public.debate"
    assert ballot.date == date(2025, 11, 19)
    assert ballot.kind == BallotKind.ORDINARY
    assert ballot.result == "rejeté" and not ballot.adopted
    assert (ballot.for_count, ballot.against_count, ballot.abstention_count) == (14, 185, 11)
    assert ballot.amendment_number == "2194"


def test_groups_and_votes(ballot):
    assert [g.group_uid for g in ballot.groups] == ["PO845401", "PO845407"]
    assert ballot.groups[0].majority_position == "contre"
    assert ballot.groups[0].against_count == 84
    against = [v for v in ballot.votes if v.position == VotePosition.AGAINST]
    assert len(against) == 84 + 21
    assert all(v.group_uid for v in ballot.votes)
    assert any(v.by_delegation for v in ballot.votes)


def test_mise_au_point_is_kept_apart(ballot):
    corrected = next(v for v in ballot.votes if v.deputy_uid == "PA2940")
    assert corrected.position == VotePosition.NON_VOTING, "as cast"
    assert corrected.corrected_position == VotePosition.AGAINST, "as declared afterwards"
