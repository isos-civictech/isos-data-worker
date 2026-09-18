"""Use case tests with plain fakes — no database, no network, no mocks."""
import pytest

from src.application.use_cases.collect_deputies import CollectDeputies
from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.ports.repositories.deputy_repository import DeputyRepository
from src.domain.ports.repositories.ingestion_log_repository import IngestionLogRepository
from src.domain.ports.sources.deputy_source import DeputySource
from src.domain.shared.results import SaveOutcome, SyncReport


def _deputy(uid: str) -> Deputy:
    return Deputy(uid=uid, first_name="Jean", last_name="Dupont")


class FakeSource(DeputySource):
    def __init__(self, deputies, groups=None):
        self._deputies = deputies
        self._groups = groups or []
        self.last_checksum = "abc123"

    def archive_url(self, legislature: int) -> str:
        return f"https://example.test/{legislature}"

    async def fetch_political_groups(self, legislature):
        return self._groups

    async def fetch_all(self, legislature, limit=None):
        return self._deputies[:limit] if limit else self._deputies

    async def fetch_by_uid(self, uid, legislature):
        return next((d for d in self._deputies if d.uid == uid), None)


class FakeRepository(DeputyRepository):
    def __init__(self, failing_uids: set[str] | None = None):
        self.saved: list[str] = []
        self.groups_saved = 0
        self._failing = failing_uids or set()

    async def save(self, deputy, *, legislature, run_id, source_url=None, checksum=None):
        if deputy.uid in self._failing:
            raise ValueError(f"malformed record {deputy.uid}")
        self.saved.append(deputy.uid)
        return SaveOutcome(entity_id=len(self.saved), created=True)

    async def save_political_groups(self, groups):
        self.groups_saved = len(groups)
        return len(groups)


class FakeLog(IngestionLogRepository):
    def __init__(self) -> None:
        self.finished: list[SyncReport] = []

    async def start_run(self, entity_type, source_url=None) -> int:
        return 1

    async def finish_run(self, run_id, report) -> None:
        self.finished.append(report)


@pytest.fixture
def log():
    return FakeLog()


async def test_a_clean_run_counts_every_deputy(log):
    repository = FakeRepository()
    use_case = CollectDeputies(
        source=FakeSource([_deputy("PA1"), _deputy("PA2"), _deputy("PA3")]),
        repository=repository,
        log_repository=log,
    )

    report = await use_case.execute(17)

    assert report.processed == 3
    assert report.created == 3
    assert report.failed == 0
    assert report.ok is True
    assert repository.saved == ["PA1", "PA2", "PA3"]


async def test_one_bad_record_does_not_abort_the_run(log):
    """A failing record is counted; the run goes on."""
    repository = FakeRepository(failing_uids={"PA2"})
    use_case = CollectDeputies(
        source=FakeSource([_deputy("PA1"), _deputy("PA2"), _deputy("PA3")]),
        repository=repository,
        log_repository=log,
    )

    report = await use_case.execute(17)

    assert repository.saved == ["PA1", "PA3"], "the run carried on past the failure"
    assert report.processed == 3
    assert report.created == 2
    assert report.failed == 1
    assert report.errors == ["PA2"], "the failing uid is kept, to be replayed by hand"


async def test_a_few_failures_stay_acceptable(log):
    """One bad record out of ten is noise, not an alarm."""
    deputies = [_deputy(f"PA{i}") for i in range(10)]
    use_case = CollectDeputies(
        source=FakeSource(deputies),
        repository=FakeRepository(failing_uids={"PA4"}),
        log_repository=log,
    )

    report = await use_case.execute(17)

    assert report.failed == 1
    assert report.ok is True


async def test_a_mostly_failing_run_is_not_ok(log):
    """Past 20% failures, the source has probably changed format."""
    uids = {f"PA{i}" for i in range(5)}
    use_case = CollectDeputies(
        source=FakeSource([_deputy(uid) for uid in sorted(uids)]),
        repository=FakeRepository(failing_uids=uids),
        log_repository=log,
    )

    report = await use_case.execute(17)

    assert report.failed == 5
    assert report.ok is False


async def test_groups_are_stored_before_deputies(log):
    """A mandate references its group by uid; the order is a constraint."""
    repository = FakeRepository()
    use_case = CollectDeputies(
        source=FakeSource(
            [_deputy("PA1")],
            groups=[PoliticalGroupRef(uid="PO1", name="Groupe", short_name="G")],
        ),
        repository=repository,
        log_repository=log,
    )

    await use_case.execute(17)

    assert repository.groups_saved == 1


async def test_dry_run_writes_nothing(log):
    repository = FakeRepository()
    use_case = CollectDeputies(
        source=FakeSource([_deputy("PA1"), _deputy("PA2")]),
        repository=repository,
        log_repository=log,
        dry_run=True,
    )

    report = await use_case.execute(17)

    assert report.processed == 2
    assert report.skipped == 2
    assert report.created == 0
    assert repository.saved == []


async def test_limit_is_honoured(log):
    use_case = CollectDeputies(
        source=FakeSource([_deputy(f"PA{i}") for i in range(10)]),
        repository=FakeRepository(),
        log_repository=log,
    )

    report = await use_case.execute(17, limit=3)

    assert report.processed == 3


async def test_the_run_is_always_closed(log):
    """Even a bad run must leave a finished row in ingestion_run."""
    use_case = CollectDeputies(
        source=FakeSource([_deputy("PA1")]),
        repository=FakeRepository(failing_uids={"PA1"}),
        log_repository=log,
    )

    await use_case.execute(17)

    assert len(log.finished) == 1
    assert log.finished[0].finished_at is not None


async def test_unknown_uid_is_reported_not_crashed(log):
    use_case = CollectDeputies(
        source=FakeSource([_deputy("PA1")]),
        repository=FakeRepository(),
        log_repository=log,
    )

    report = await use_case.execute_one("PA-does-not-exist", 17)

    assert report.processed == 0
    assert report.failed == 0
