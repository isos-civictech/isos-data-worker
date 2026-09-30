"""Project sittings from `raw` into `public`. SQL only, no network."""

from loguru import logger

from src.domain.ports.projections.debate_projection import DebateProjection
from src.domain.shared.results import SyncReport


class ProjectDebates:
    def __init__(self, *, projection: DebateProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=debate legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
