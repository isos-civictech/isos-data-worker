"""
Everything, in dependency order, in one call.

Full run:     every dataset, every row.
Scoped run:   `debates=N` — every deputy, then only the N most recent sittings
              and what hangs off them: their comptes rendus, the laws on their
              agenda, those laws' amendments, texts and scrutins. The archives
              are still read whole (the AN publishes one per legislature);
              only what is kept in the database is scoped.
"""

from datetime import UTC, datetime

from loguru import logger

from src.application.use_cases.collect_agenda import CollectAgenda
from src.application.use_cases.collect_amendments import CollectAmendments
from src.application.use_cases.collect_ballots import CollectBallots
from src.application.use_cases.collect_debates import CollectDebates
from src.application.use_cases.collect_deputies import CollectDeputies
from src.application.use_cases.collect_law_texts import CollectLawTexts
from src.application.use_cases.collect_laws import CollectLaws
from src.application.use_cases.project_agenda import ProjectAgenda
from src.application.use_cases.project_amendments import ProjectAmendments
from src.application.use_cases.project_ballots import ProjectBallots
from src.application.use_cases.project_debates import ProjectDebates
from src.application.use_cases.project_deputies import ProjectDeputies
from src.application.use_cases.project_law_texts import ProjectLawTexts
from src.application.use_cases.project_laws import ProjectLaws
from src.domain.ports.repositories.agenda_repository import AgendaRepository
from src.domain.shared.results import SyncReport


class SyncAll:
    def __init__(
        self,
        *,
        agenda_repository: AgendaRepository,
        collect_deputies: CollectDeputies,
        collect_agenda: CollectAgenda,
        collect_debates: CollectDebates,
        collect_laws: CollectLaws,
        collect_amendments: CollectAmendments,
        collect_ballots: CollectBallots,
        collect_law_texts: CollectLawTexts,
        project_deputies: ProjectDeputies,
        project_laws: ProjectLaws,
        project_agenda: ProjectAgenda,
        project_debates: ProjectDebates,
        project_amendments: ProjectAmendments,
        project_ballots: ProjectBallots,
        project_law_texts: ProjectLawTexts,
    ) -> None:
        self._agenda_repository = agenda_repository
        self._collect = {
            "deputies": collect_deputies,
            "agenda": collect_agenda,
            "debates": collect_debates,
            "laws": collect_laws,
            "amendments": collect_amendments,
            "ballots": collect_ballots,
            "law_texts": collect_law_texts,
        }
        self._project = [
            ("deputies", project_deputies),
            ("laws", project_laws),
            ("agenda", project_agenda),
            ("debates", project_debates),
            ("amendments", project_amendments),
            ("law_texts", project_law_texts),
            ("ballots", project_ballots),
        ]

    async def execute(self, legislature: int, *, debates: int | None = None) -> dict[str, dict]:
        """Reports by step, in the order they ran."""
        reports: dict[str, SyncReport] = {}
        logger.info("sync.start legislature={} scope={}", legislature, debates or "all")

        reports["collect.deputies"] = await self._collect["deputies"].execute(legislature)
        reports["collect.agenda"] = await self._collect["agenda"].execute(legislature, last=debates)

        if debates is None:
            reports["collect.debates"] = await self._collect["debates"].execute(legislature)
            reports["collect.laws"] = await self._collect["laws"].execute(legislature)
            reports["collect.amendments"] = await self._collect["amendments"].execute(legislature)
            reports["collect.law_texts"] = await self._collect["law_texts"].execute(legislature)
            reports["collect.ballots"] = await self._collect["ballots"].execute(legislature)
        else:
            sittings = await self._agenda_repository.latest_held(
                legislature, debates, before=datetime.now(tz=UTC)
            )
            agenda_uids = {s.uid for s in sittings}
            compte_rendus = {s.compte_rendu_uid for s in sittings if s.compte_rendu_uid}
            dossiers = set().union(*(s.dossier_uids for s in sittings)) if sittings else set()
            logger.info(
                "sync.scope sittings={} comptes_rendus={} dossiers={}",
                len(agenda_uids),
                len(compte_rendus),
                len(dossiers),
            )
            reports["collect.debates"] = await self._collect["debates"].execute(
                legislature, uids=compte_rendus
            )
            reports["collect.laws"] = await self._collect["laws"].execute(
                legislature, dossier_uids=dossiers
            )
            reports["collect.amendments"] = _merge(
                "amendment",
                [
                    await self._collect["amendments"].execute(legislature, dossier_uid=d)
                    for d in sorted(dossiers)
                ],
            )
            reports["collect.law_texts"] = _merge(
                "law_text",
                [
                    await self._collect["law_texts"].execute(legislature, dossier_uid=d)
                    for d in sorted(dossiers)
                ],
            )
            reports["collect.ballots"] = await self._collect["ballots"].execute(
                legislature, agenda_uids=agenda_uids
            )

        for name, use_case in self._project:
            reports[f"project.{name}"] = await use_case.execute(legislature)

        logger.info("sync.done steps={}", len(reports))
        return {step: report.as_dict() for step, report in reports.items()}


def _merge(entity: str, reports: list[SyncReport]) -> SyncReport:
    """One report for a step run once per dossier."""
    total = SyncReport(entity=entity)
    for r in reports:
        total.processed += r.processed
        total.created += r.created
        total.updated += r.updated
        total.skipped += r.skipped
        total.failed += r.failed
        total.errors.extend(r.errors[: total.ERROR_SAMPLE_SIZE - len(total.errors)])
    return total.finish()
