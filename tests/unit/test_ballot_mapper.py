from datetime import date

from src.domain.entities.ballot import Ballot
from src.infrastructure.persistence.serving.ballot_projection import _matching_words
from src.infrastructure.persistence.serving.mappers.ballot_mapper import (
    ballot_row,
    deputy_vote_row,
)


def test_amendment_number_patterns():
    base = dict(
        uid="V", legislature=17, number=1, sitting_uid="S", date=date(2025, 1, 1), kind="SPO"
    )
    assert Ballot(**base, title="l'amendement n° 585 de M. Pauget").amendment_number == "585"
    assert (
        Ballot(**base, title="l’amendement de suppression n° 444 (rect.)").amendment_number == "444"
    )
    assert Ballot(**base, title="le sous-amendement n° 40 de M. Dufau").amendment_number == "40"
    assert Ballot(**base, title="l'ensemble du projet de loi").amendment_number is None


def test_ballot_row_translates_enums():
    raw = {
        "uid": "V1",
        "kind": "MOC",
        "title": "la motion de censure",
        "date": date(2025, 1, 1),
        "result": "rejeté",
        "for_count": 200,
        "against_count": 0,
        "abstention_count": 0,
    }
    row = ballot_row(raw, debate_id=3, law_id=None, amendment_id=None, reading_id=None)
    assert (row["type"], row["result"], row["calendar_status"]) == (
        "censure_motion",
        "rejected",
        "completed",
    )
    assert row["ballot_date"].tzinfo is not None
    assert row["external_id"] == "V1"


def test_deputy_vote_shows_the_correction():
    raw = {"position": "nonVotant", "corrected_position": "contre"}
    assert deputy_vote_row(raw, ballot_id=1, deputy_id=2, group_id=None)["position"] == "against"
    raw = {"position": "nonVotantVolontaire", "corrected_position": None}
    assert deputy_vote_row(raw, ballot_id=1, deputy_id=2, group_id=None)["position"] == "absent"


def test_matching_words():
    law = "restaurer-un-systeme-de-retraite-plus-juste"
    ballot = (
        "l-article-2-de-la-proposition-de-loi-visant-a-restaurer-un-systeme-de-retraite-plus-juste"
    )
    assert _matching_words(law, ballot) == 7
    assert _matching_words("assouplir-les-conditions", ballot) == 0
