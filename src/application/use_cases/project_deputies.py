"""
Project deputies from `raw` into `public`. SQL only — no network, so it can be
re-run at will after a mapping fix.
"""

from loguru import logger

from src.domain.ports.projections.deputy_projection import DeputyProjection
from src.domain.shared.results import SyncReport


class ProjectDeputies:
    def __init__(self, *, projection: DeputyProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=deputy legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
