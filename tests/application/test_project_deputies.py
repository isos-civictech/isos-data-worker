from src.application.use_cases.project_deputies import ProjectDeputies
from src.domain.ports.projections.deputy_projection import DeputyProjection
from src.domain.shared.results import SyncReport


class FakeProjection(DeputyProjection):
    def __init__(self) -> None:
        self.calls: list[int] = []

    async def project_all(self, legislature: int) -> SyncReport:
        self.calls.append(legislature)
        return SyncReport(entity="deputy-projection", processed=3, created=3).finish()


async def test_delegates_to_the_projection_port():
    projection = FakeProjection()
    report = await ProjectDeputies(projection=projection).execute(17)

    assert projection.calls == [17]
    assert report.ok is True
