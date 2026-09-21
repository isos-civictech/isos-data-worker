"""
Command line entry point (used by Kubernetes Jobs and the Makefile). Exit code
0 if the run is acceptable, 1 otherwise.

    collect-<dataset>   Assemblée nationale → raw        (S3 first, --refresh to re-download)
    project-<dataset>   raw → public                     (SQL only, no network)
    sync-all            everything in order; --debates N keeps only the N latest sittings
    refresh             re-download the archives into S3, database untouched
"""

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import date

from loguru import logger

from src.composition import Worker, build_engine, build_worker
from src.config import get_settings
from src.interfaces.dispatch import DATASETS, Selection, collect, project
from src.logging_setup import setup_logging


async def _run(args, action: Callable[[Worker], Awaitable]):
    settings = get_settings()
    engine = build_engine(settings)
    try:
        async with build_worker(
            settings, engine, dry_run=args.dry_run, refresh=args.refresh
        ) as worker:
            return await action(worker)
    finally:
        await engine.dispose()


def _collect(args, w: Worker):
    return collect(
        w,
        args.dataset,
        args.legislature,
        Selection(
            limit=args.limit, uid=args.uid, dossier=args.dossier, since=args.since, until=args.until
        ),
    )


def _project(args, w: Worker):
    return project(w, args.dataset, args.legislature)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="isos-data-worker", description=__doc__)
    parser.add_argument("--legislature", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="fetch and parse, write nothing")
    parser.add_argument("--refresh", action="store_true", help="re-download archives to S3")
    sub = parser.add_subparsers(dest="command", required=True)

    for dataset in DATASETS:
        c = sub.add_parser(f"collect-{dataset}", help=f"Assemblée nationale → raw ({dataset})")
        c.add_argument("--limit", type=int, default=None, help="stop after N items")
        c.add_argument("--uid", default=None, help="one item only")
        c.add_argument("--dossier", default=None, help="one dossier only (DLR…)")
        c.add_argument("--date", type=date.fromisoformat, default=None, help="one day")
        c.add_argument("--since", type=date.fromisoformat, default=None)
        c.add_argument("--until", type=date.fromisoformat, default=None)
        c.set_defaults(dataset=dataset, handler=_collect)

        p = sub.add_parser(f"project-{dataset}", help=f"raw → public ({dataset}), no network")
        p.set_defaults(dataset=dataset, handler=_project)

    s = sub.add_parser("sync-all", help="collect then project every dataset, in order")
    s.add_argument(
        "--debates",
        type=int,
        default=None,
        help="scope: every deputy, then only the N latest sittings and what they touch",
    )
    s.set_defaults(
        handler=lambda args, w: w.sync_all.execute(args.legislature, debates=args.debates)
    )

    r = sub.add_parser("refresh", help="re-download the archives into S3 (database untouched)")
    r.add_argument("datasets", nargs="*", help="deputies laws agenda debates amendments ballots")
    r.set_defaults(
        handler=lambda args, w: w.refresh_archives.execute(args.legislature, args.datasets or None)
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)
    if args.legislature is None:
        args.legislature = settings.an_legislature
    if getattr(args, "date", None):
        args.since = args.until = args.date
    logger.info("target database={}", settings.safe_database_target)

    result = asyncio.run(_run(args, lambda w: args.handler(args, w)))
    if hasattr(result, "as_dict"):  # one SyncReport
        print(json.dumps(result.as_dict(), default=str))
        return 0 if result.ok else 1
    print(json.dumps(result, default=str, indent=1))  # sync-all / refresh
    reports = [r for r in result.values() if isinstance(r, dict) and "ok" in r]
    return 0 if all(r["ok"] or r["processed"] == 0 for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
