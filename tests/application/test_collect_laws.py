from src.application.use_cases.collect_laws import CollectLaws
from src.domain.entities.law import Law
from src.domain.ports.repositories.law_repository import LawRepository
from src.domain.ports.sources.law_source import LawSource
from src.domain.shared.results import SaveOutcome
from tests.application.test_collect_deputies import FakeLog


def _law(uid: str) -> Law:
    return Law(dossier_uid=uid, legislature=17, title=f"Loi {uid}", procedure_code="2")


class FakeSource(LawSource):
    def __init__(self, laws):
        self._laws = laws

    async def fetch_all(self, legislature, limit=None):
        return self._laws[:limit] if limit else self._laws

    async def fetch_by_uid(self, uid, legislature):
        return next((law for law in self._laws if law.dossier_uid == uid), None)


class FakeRepository(LawRepository):
    def __init__(self, failing=()):
        self.saved = []
        self._failing = set(failing)

    async def save(self, law, *, run_id, s3_key=None):
        if law.dossier_uid in self._failing:
            raise ValueError("bad dossier")
        self.saved.append(law.dossier_uid)
        return SaveOutcome(entity_id=len(self.saved), created=True)


async def test_one_bad_dossier_does_not_stop_the_run():
    repo = FakeRepository(failing={"B"})
    log = FakeLog()
    report = await CollectLaws(
        source=FakeSource([_law("A"), _law("B"), _law("C")]), repository=repo, log_repository=log
    ).execute(17)

    assert (report.processed, report.created, report.failed) == (3, 2, 1)
    assert report.errors == ["B"]
    assert repo.saved == ["A", "C"]
    assert log.finished


async def test_dry_run_writes_nothing():
    repo = FakeRepository()
    report = await CollectLaws(
        source=FakeSource([_law("A")]), repository=repo, log_repository=FakeLog(), dry_run=True
    ).execute(17)
    assert report.skipped == 1
    assert repo.saved == []


async def test_execute_one_unknown_uid_is_an_empty_run():
    report = await CollectLaws(
        source=FakeSource([]), repository=FakeRepository(), log_repository=FakeLog()
    ).execute_one("DLR-nope", 17)
    assert report.processed == 0
    assert not report.ok, "an empty run is not a success (exit code 1)"
