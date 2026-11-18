"""
First fill of an empty database: everything the public pages show without
needing a debate. Deputies (with their groups and mandates), the whole agenda
(past and future sittings), laws, amendments, scrutins and votes.

Debates, and what hangs off them, come later, sitting by sitting.
"""

from loguru import logger

from src.application.use_cases.collect_agenda import CollectAgenda
from src.application.use_cases.collect_amendments import CollectAmendments
from src.application.use_cases.collect_ballots import CollectBallots
from src.application.use_cases.collect_deputies import CollectDeputies
from src.application.use_cases.collect_laws import CollectLaws
from src.application.use_cases.project_agenda import ProjectAgenda
from src.application.use_cases.project_amendments import ProjectAmendments
from src.application.use_cases.project_ballots import ProjectBallots
from src.application.use_cases.project_deputies import ProjectDeputies
from src.application.use_cases.project_laws import ProjectLaws


class InitDatabase:
    def __init__(
        self,
        *,
        collect_deputies: CollectDeputies,
        collect_agenda: CollectAgenda,
        collect_laws: CollectLaws,
        collect_amendments: CollectAmendments,
        collect_ballots: CollectBallots,
        project_deputies: ProjectDeputies,
        project_agenda: ProjectAgenda,
        project_laws: ProjectLaws,
        project_amendments: ProjectAmendments,
        project_ballots: ProjectBallots,
    ) -> None:
        self._steps = [
            ("collect.deputies", collect_deputies),
            ("collect.agenda", collect_agenda),
            ("collect.laws", collect_laws),
            ("collect.amendments", collect_amendments),
            ("collect.ballots", collect_ballots),
            ("project.deputies", project_deputies),
            ("project.agenda", project_agenda),
            ("project.laws", project_laws),
            ("project.amendments", project_amendments),
            ("project.ballots", project_ballots),
        ]

    async def execute(self, legislature: int) -> dict[str, dict]:
        """Reports by step, in the order they ran. Laws come before amendments, which need them."""
        logger.info("init.start legislature={}", legislature)
        reports = {}
        for name, use_case in self._steps:
            reports[name] = (await use_case.execute(legislature)).as_dict()
        logger.info("init.done steps={}", len(reports))
        return reports
