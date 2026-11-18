from datetime import date, timedelta

from src.application.use_cases.purge_raw import PurgeRaw
from src.domain.ports.repositories.raw_purge import RawPurge


class FakePurge(RawPurge):
    def __init__(self):
        self.calls = []

    async def purge(self, before, *, dry_run=False):
        self.calls.append((before, dry_run))
        return {"ballot_vote": 3}


async def test_purges_items_older_than_the_retention():
    fake = FakePurge()

    counts = await PurgeRaw(repository=fake, retention_days=90).execute()

    assert counts == {"ballot_vote": 3}
    before, dry_run = fake.calls[0]
    assert before == date.today() - timedelta(days=90) and dry_run is False


async def test_a_retention_of_zero_disables_the_purge():
    fake = FakePurge()

    assert await PurgeRaw(repository=fake, retention_days=0).execute() == {}
    assert fake.calls == []


async def test_dry_run_and_explicit_days_are_passed_through():
    fake = FakePurge()

    await PurgeRaw(repository=fake, retention_days=90).execute(dry_run=True, days=30)

    assert fake.calls[0] == (date.today() - timedelta(days=30), True)
