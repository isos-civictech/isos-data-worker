"""Project the sittings agenda from `raw` into `public.debate`. SQL only."""

from loguru import logger

from src.domain.ports.projections.agenda_projection import AgendaProjection
from src.domain.shared.results import SyncReport


class ProjectAgenda:
    def __init__(self, *, projection: AgendaProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=agenda legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
