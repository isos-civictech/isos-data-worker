from src.application.use_cases.collect_amendments import BATCH_SIZE, CollectAmendments
from src.domain.entities.amendment import Amendment
from src.domain.ports.repositories.amendment_repository import AmendmentRepository
from src.domain.ports.sources.amendment_source import AmendmentSource
from src.domain.shared.results import BatchOutcome
from tests.application.test_collect_deputies import FakeLog


def _a(i: int) -> Amendment:
    return Amendment(uid=f"AM{i}", legislature=17, texte_uid="T", author_type="Député")


class FakeSource(AmendmentSource):
    def __init__(self, n: int):
        self._n = n

    async def iter_all(self, legislature, *, dossier_uid=None, since=None, limit=None):
        for i in range(limit or self._n):
            yield _a(i)


class FakeRepository(AmendmentRepository):
    def __init__(self, fail_batch: int | None = None):
        self.batches: list[int] = []
        self._fail = fail_batch

    async def save_batch(self, amendments, *, run_id, s3_key=None):
        self.batches.append(len(amendments))
        if self._fail == len(self.batches):
            raise ValueError("bad batch")
        return BatchOutcome(created=len(amendments), updated=0)


async def test_batches_and_last_partial_flush():
    repo = FakeRepository()
    report = await CollectAmendments(
        source=FakeSource(BATCH_SIZE * 2 + 3), repository=repo, log_repository=FakeLog()
    ).execute(17)
    assert repo.batches == [BATCH_SIZE, BATCH_SIZE, 3]
    assert (report.processed, report.created, report.failed) == (
        BATCH_SIZE * 2 + 3,
        report.processed,
        0,
    )


async def test_failed_batch_counts_its_rows_and_run_continues():
    repo = FakeRepository(fail_batch=1)
    report = await CollectAmendments(
        source=FakeSource(BATCH_SIZE + 1), repository=repo, log_repository=FakeLog()
    ).execute(17)
    assert (report.failed, report.created) == (BATCH_SIZE, 1)
    assert len(report.errors) == report.ERROR_SAMPLE_SIZE


async def test_dry_run():
    repo = FakeRepository()
    report = await CollectAmendments(
        source=FakeSource(5), repository=repo, log_repository=FakeLog(), dry_run=True
    ).execute(17)
    assert repo.batches == [] and report.skipped == 5
