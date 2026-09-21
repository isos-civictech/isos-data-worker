"""
Command line entry point (used by Kubernetes Jobs). Exit code 0 if the run is
acceptable, 1 otherwise.
"""

import argparse
import asyncio
from datetime import date

from loguru import logger

from src.composition import (
    build_collect_agenda,
    build_collect_debates,
    build_collect_deputies,
    build_collect_laws,
    build_engine,
    build_project_agenda,
    build_project_debates,
    build_project_deputies,
    build_project_laws,
)
from src.config import get_settings
from src.domain.shared.results import SyncReport
from src.logging_setup import setup_logging


async def _collect_deputies(args) -> SyncReport:
    settings = get_settings()
    engine = build_engine(settings)
    try:
        async with build_collect_deputies(settings, engine, dry_run=args.dry_run) as use_case:
            if args.uid:
                return await use_case.execute_one(args.uid, args.legislature)
            return await use_case.execute(args.legislature, limit=args.limit)
    finally:
        await engine.dispose()


async def _project_deputies(args) -> SyncReport:
    engine = build_engine(get_settings())
    try:
        return await build_project_deputies(engine).execute(args.legislature)
    finally:
        await engine.dispose()


async def _collect_debates(args) -> SyncReport:
    settings = get_settings()
    engine = build_engine(settings)
    try:
        async with build_collect_debates(settings, engine, dry_run=args.dry_run) as use_case:
            if args.uid:
                return await use_case.execute_one(args.uid, args.legislature)
            return await use_case.execute(
                args.legislature, limit=args.limit, since=args.since, until=args.until
            )
    finally:
        await engine.dispose()


async def _project_debates(args) -> SyncReport:
    engine = build_engine(get_settings())
    try:
        return await build_project_debates(engine).execute(args.legislature)
    finally:
        await engine.dispose()


async def _collect_agenda(args) -> SyncReport:
    settings = get_settings()
    engine = build_engine(settings)
    try:
        async with build_collect_agenda(settings, engine, dry_run=args.dry_run) as use_case:
            return await use_case.execute(
                args.legislature, limit=args.limit, since=args.since, until=args.until
            )
    finally:
        await engine.dispose()


async def _project_agenda(args) -> SyncReport:
    engine = build_engine(get_settings())
    try:
        return await build_project_agenda(engine).execute(args.legislature)
    finally:
        await engine.dispose()


async def _collect_laws(args) -> SyncReport:
    settings = get_settings()
    engine = build_engine(settings)
    try:
        async with build_collect_laws(settings, engine, dry_run=args.dry_run) as use_case:
            if args.uid:
                return await use_case.execute_one(args.uid, args.legislature)
            return await use_case.execute(args.legislature, limit=args.limit)
    finally:
        await engine.dispose()


async def _project_laws(args) -> SyncReport:
    engine = build_engine(get_settings())
    try:
        return await build_project_laws(engine).execute(args.legislature)
    finally:
        await engine.dispose()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="isos-data-worker")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect-deputies", help="Assemblée nationale → raw.deputy")
    collect.add_argument("--legislature", type=int, default=None)
    collect.add_argument(
        "--limit", type=int, default=None, help="stop after N deputies (development)"
    )
    collect.add_argument("--uid", default=None, help="replay a single deputy")
    collect.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch and parse, write nothing",
    )
    collect.set_defaults(handler=_collect_deputies)

    project = sub.add_parser("project-deputies", help="raw.deputy → public.deputy (no network)")
    project.add_argument("--legislature", type=int, default=None)
    project.set_defaults(handler=_project_deputies)

    collect_d = sub.add_parser("collect-debates", help="Assemblée nationale → raw.debate")
    collect_d.add_argument("--legislature", type=int, default=None)
    collect_d.add_argument("--limit", type=int, default=None, help="stop after N sittings")
    collect_d.add_argument("--uid", default=None, help="replay a single sitting")
    collect_d.add_argument(
        "--date", type=date.fromisoformat, default=None, help="one day (YYYY-MM-DD)"
    )
    collect_d.add_argument("--since", type=date.fromisoformat, default=None, help="from this day")
    collect_d.add_argument("--until", type=date.fromisoformat, default=None, help="up to this day")
    collect_d.add_argument("--dry-run", action="store_true")
    collect_d.set_defaults(handler=_collect_debates)

    project_d = sub.add_parser("project-debates", help="raw.debate → public.debate (no network)")
    project_d.add_argument("--legislature", type=int, default=None)
    project_d.set_defaults(handler=_project_debates)

    collect_a = sub.add_parser("collect-agenda", help="Assemblée nationale → raw.agenda_item")
    collect_a.add_argument("--legislature", type=int, default=None)
    collect_a.add_argument("--limit", type=int, default=None)
    collect_a.add_argument("--date", type=date.fromisoformat, default=None, help="one day")
    collect_a.add_argument("--since", type=date.fromisoformat, default=None)
    collect_a.add_argument("--until", type=date.fromisoformat, default=None)
    collect_a.add_argument("--dry-run", action="store_true")
    collect_a.set_defaults(handler=_collect_agenda)

    project_a = sub.add_parser(
        "project-agenda", help="raw.agenda_item → public.debate (no network)"
    )
    project_a.add_argument("--legislature", type=int, default=None)
    project_a.set_defaults(handler=_project_agenda)

    collect_l = sub.add_parser("collect-laws", help="Assemblée nationale → raw.law")
    collect_l.add_argument("--legislature", type=int, default=None)
    collect_l.add_argument("--limit", type=int, default=None, help="stop after N dossiers")
    collect_l.add_argument("--uid", default=None, help="replay a single dossier (DLR…)")
    collect_l.add_argument("--dry-run", action="store_true")
    collect_l.set_defaults(handler=_collect_laws)

    project_l = sub.add_parser(
        "project-laws", help="raw.law → public.law, law_reading, debate_law (no network)"
    )
    project_l.add_argument("--legislature", type=int, default=None)
    project_l.set_defaults(handler=_project_laws)

    return parser


def main() -> int:
    args = _parser().parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    if getattr(args, "legislature", None) is None:
        args.legislature = settings.an_legislature
    if getattr(args, "date", None):
        args.since = args.until = args.date

    logger.info("target database={}", settings.safe_database_target)

    report = asyncio.run(args.handler(args))
    print(report.as_dict())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
