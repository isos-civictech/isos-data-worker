"""Project dossiers from `raw` into `public.law` and friends. SQL only."""

from loguru import logger

from src.domain.ports.projections.law_projection import LawProjection
from src.domain.shared.results import SyncReport


class ProjectLaws:
    def __init__(self, *, projection: LawProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=law legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
