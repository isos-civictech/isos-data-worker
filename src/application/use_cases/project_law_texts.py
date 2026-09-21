"""Project law texts from `raw` into `public.law_text` / `public.law_article`. SQL only."""

from loguru import logger

from src.domain.ports.projections.law_text_projection import LawTextProjection
from src.domain.shared.results import SyncReport


class ProjectLawTexts:
    def __init__(self, *, projection: LawTextProjection) -> None:
        self._projection = projection

    async def execute(self, legislature: int) -> SyncReport:
        logger.info("project.start entity=law_text legislature={}", legislature)
        report = await self._projection.project_all(legislature)
        logger.info("project.done {}", report.as_dict())
        return report
