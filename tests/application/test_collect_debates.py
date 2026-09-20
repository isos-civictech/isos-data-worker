from datetime import datetime

import pytest

from src.application.use_cases.collect_debates import CollectDebates
from src.domain.entities.debate import Debate
from src.domain.ports.repositories.debate_repository import DebateRepository
from src.domain.ports.sources.debate_source import DebateSource
from src.domain.shared.results import SaveOutcome
from tests.application.test_collect_deputies import FakeLog


def _debate(uid: str) -> Debate:
    return Debate(uid=uid, legislature=17, date=datetime(2024, 11, 6, 14))


class FakeSource(DebateSource):
    def __init__(self, debates):
        self._debates = debates
        self.last_s3_key = "raw/debates/17/syceron.xml.zip"

    async def fetch_all(self, legislature, limit=None):
        return self._debates[:limit] if limit else self._debates

    async def fetch_by_uid(self, uid, legislature):
        return next((d for d in self._debates if d.uid == uid), None)


class FakeRepository(DebateRepository):
    def __init__(self, failing=()):
        self.saved = []
        self._failing = set(failing)

    async def save(self, debate, *, run_id, s3_key=None):
        if debate.uid in self._failing:
            raise ValueError("bad sitting")
        self.saved.append(debate.uid)
        return SaveOutcome(entity_id=len(self.saved), created=True)


@pytest.fixture
def log():
    return FakeLog()


async def test_clean_run(log):
    repo = FakeRepository()
    report = await CollectDebates(
        source=FakeSource([_debate("A"), _debate("B")]), repository=repo, log_repository=log
    ).execute(17)
    assert report.created == 2
    assert repo.saved == ["A", "B"]


async def test_one_bad_sitting_does_not_abort(log):
    repo = FakeRepository(failing={"B"})
    report = await CollectDebates(
        source=FakeSource([_debate("A"), _debate("B"), _debate("C")]),
        repository=repo,
        log_repository=log,
    ).execute(17)
    assert repo.saved == ["A", "C"]
    assert report.failed == 1
    assert report.errors == ["B"]


async def test_dry_run_writes_nothing(log):
    repo = FakeRepository()
    report = await CollectDebates(
        source=FakeSource([_debate("A")]), repository=repo, log_repository=log, dry_run=True
    ).execute(17)
    assert report.skipped == 1
    assert repo.saved == []
