from datetime import date

from src.application.use_cases.collect_ballots import CollectBallots
from src.domain.entities.ballot import Ballot
from src.domain.ports.repositories.ballot_repository import BallotRepository
from src.domain.ports.sources.ballot_source import BallotSource
from src.domain.shared.results import SaveOutcome
from tests.application.test_collect_deputies import FakeLog


def _ballot(uid: str) -> Ballot:
    return Ballot(
        uid=uid, legislature=17, number=1, agenda_uid="S", date=date(2025, 1, 1), kind="SPO"
    )


class FakeSource(BallotSource):
    def __init__(self, ballots):
        self._ballots = ballots

    async def fetch_all(self, legislature, *, since=None, until=None, limit=None):
        return self._ballots[:limit] if limit else self._ballots

    async def fetch_by_uid(self, uid, legislature):
        return next((b for b in self._ballots if b.uid == uid), None)


class FakeRepository(BallotRepository):
    def __init__(self, failing=()):
        self.saved = []
        self._failing = set(failing)

    async def save(self, ballot, *, run_id, s3_key=None):
        if ballot.uid in self._failing:
            raise ValueError("bad scrutin")
        self.saved.append(ballot.uid)
        return SaveOutcome(entity_id=len(self.saved), created=True)


async def test_one_bad_scrutin_does_not_stop_the_run():
    repo = FakeRepository(failing={"B"})
    report = await CollectBallots(
        source=FakeSource([_ballot("A"), _ballot("B"), _ballot("C")]),
        repository=repo,
        log_repository=FakeLog(),
    ).execute(17)
    assert (report.processed, report.created, report.failed) == (3, 2, 1)
    assert repo.saved == ["A", "C"]


async def test_execute_one():
    repo = FakeRepository()
    report = await CollectBallots(
        source=FakeSource([_ballot("A")]), repository=repo, log_repository=FakeLog()
    ).execute_one("A", 17)
    assert report.created == 1 and repo.saved == ["A"]
