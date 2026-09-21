"""Project amendments from `raw` into `public.amendment`. SQL only."""

from loguru import logger

from src.domain.ports.projections.amendment_projection import AmendmentProjection
from src.domain.shared.results import SyncReport


class ProjectAmendments:
    def __init__(self, *, projection: AmendmentProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=amendment legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
