"""One place that knows which use case serves which dataset, for the CLI and the API."""

from dataclasses import dataclass
from datetime import date

from src.composition import Worker
from src.domain.shared.results import SyncReport

DATASETS = ("deputies", "laws", "agenda", "debates", "amendments", "ballots", "law-texts")


@dataclass(frozen=True)
class Selection:
    """What to collect: everything by default, narrowed by these filters."""

    limit: int | None = None
    uid: str | None = None  # one item (deputy, dossier, sitting, scrutin, text)
    dossier: str | None = None  # one dossier (amendments, law texts)
    since: date | None = None
    until: date | None = None


async def collect(worker: Worker, dataset: str, legislature: int, s: Selection) -> SyncReport:
    match dataset:
        case "deputies":
            if s.uid:
                return await worker.collect_deputies.execute_one(s.uid, legislature)
            return await worker.collect_deputies.execute(legislature, limit=s.limit)
        case "laws":
            if s.uid:
                return await worker.collect_laws.execute_one(s.uid, legislature)
            return await worker.collect_laws.execute(legislature, limit=s.limit)
        case "agenda":
            return await worker.collect_agenda.execute(
                legislature, limit=s.limit, since=s.since, until=s.until
            )
        case "debates":
            if s.uid:
                return await worker.collect_debates.execute_one(s.uid, legislature)
            return await worker.collect_debates.execute(
                legislature, limit=s.limit, since=s.since, until=s.until
            )
        case "amendments":
            return await worker.collect_amendments.execute(
                legislature, dossier_uid=s.dossier, since=s.since, limit=s.limit
            )
        case "ballots":
            if s.uid:
                return await worker.collect_ballots.execute_one(s.uid, legislature)
            return await worker.collect_ballots.execute(
                legislature, since=s.since, until=s.until, limit=s.limit
            )
        case "law-texts":
            return await worker.collect_law_texts.execute(
                legislature, dossier_uid=s.dossier, texte_uid=s.uid, limit=s.limit
            )
    raise ValueError(f"unknown dataset {dataset!r}, expected one of {DATASETS}")


async def project(worker: Worker, dataset: str, legislature: int) -> SyncReport:
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}, expected one of {DATASETS}")
    return await getattr(worker, "project_" + dataset.replace("-", "_")).execute(legislature)
