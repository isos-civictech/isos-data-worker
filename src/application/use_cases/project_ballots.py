"""Project scrutins from `raw` into `public.ballot` and `public.deputy_vote`. SQL only."""

from loguru import logger

from src.domain.ports.projections.ballot_projection import BallotProjection
from src.domain.shared.results import SyncReport


class ProjectBallots:
    def __init__(self, *, projection: BallotProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=ballot legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
