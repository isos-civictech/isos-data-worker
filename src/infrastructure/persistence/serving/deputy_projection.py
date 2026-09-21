"""
raw -> public projection for deputies.

`public.deputy` and `public.political_group` have no unique index on
external_id, so the upsert is a lookup then insert-or-update rather than
ON CONFLICT. Slugs are written once and never updated: a title fix upstream
must not break an already-indexed URL.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.ports.projections.deputy_projection import DeputyProjection
from src.domain.shared.legislatures import legislature_start
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.deputy_mapper import (
    deputy_row,
    mandate_row,
    political_group_row,
)
from src.infrastructure.persistence.serving.slug import unique_slug


async def ensure_legislature(connection: AsyncConnection, number: int) -> int:
    """
    ON CONFLICT DO UPDATE with a no-op set: DO NOTHING returns no row on
    conflict, and we need the id either way.
    """
    statement = (
        insert(pub.legislature)
        .values(number=number, started_at=legislature_start(number))
        .on_conflict_do_update(index_elements=["number"], set_={"number": number})
        .returning(pub.legislature.c.id)
    )
    return (await connection.execute(statement)).scalar_one()


async def _upsert_by_external_id(
    connection: AsyncConnection,
    table: sa.Table,
    row: dict,
    *,
    write_once: tuple[str, ...] = (),
    extra_where=None,
) -> tuple[int, bool]:
    """Lookup on external_id, then INSERT or UPDATE. Returns (id, created)."""
    where = table.c.external_id == row["external_id"]
    if extra_where is not None:
        where = sa.and_(where, extra_where)
    existing = (await connection.execute(sa.select(table.c.id).where(where))).scalar()

    if existing is None:
        inserted = await connection.execute(insert(table).values(**row).returning(table.c.id))
        return inserted.scalar_one(), True

    updates = {k: v for k, v in row.items() if k not in write_once}
    if "updated_at" in table.c:
        updates["updated_at"] = sa.func.now()
    await connection.execute(sa.update(table).where(table.c.id == existing).values(**updates))
    return existing, False


class SqlDeputyProjection(DeputyProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="deputy-projection")

        async with transaction(self._engine) as connection:
            legislature_id = await ensure_legislature(connection, legislature)
            group_ids = await self._project_groups(connection, legislature_id)

        raw_deputies = await self._load_raw_deputies(legislature)

        for deputy, mandates in raw_deputies:
            report.processed += 1
            if not mandates:
                # A minister who never sat: kept in raw, not a deputy for the front.
                report.skipped += 1
                continue
            try:
                async with transaction(self._engine) as connection:
                    created = await self._project_one(
                        connection, deputy, mandates, legislature_id, group_ids
                    )
                report.created += int(created)
                report.updated += int(not created)
            except Exception:
                report.record_failure(deputy["uid"])
                raise

        return report.finish()

    async def _project_groups(self, connection: AsyncConnection, legislature_id: int) -> dict:
        """uid AN -> public.political_group.id, for the whole run."""
        rows = (await connection.execute(sa.select(raw.political_group))).mappings().all()
        ids: dict[str, int] = {}
        for group in rows:
            group_id, _ = await _upsert_by_external_id(
                connection,
                pub.political_group,
                political_group_row(group, legislature_id=legislature_id),
                extra_where=pub.political_group.c.legislature_id == legislature_id,
            )
            ids[group["uid"]] = group_id
        return ids

    async def _load_raw_deputies(self, legislature: int) -> list[tuple[dict, list[dict]]]:
        """Each deputy with its seats, oldest first (a deputy can have several)."""
        async with self._engine.connect() as connection:
            deputies = (
                (
                    await connection.execute(
                        sa.select(raw.deputy)
                        .where(raw.deputy.c.legislature == legislature)
                        .order_by(raw.deputy.c.uid)
                    )
                )
                .mappings()
                .all()
            )
            mandates = (
                (
                    await connection.execute(
                        sa.select(raw.mandate)
                        .where(raw.mandate.c.legislature == legislature)
                        # Same start date twice (AN quirk): the longer seat comes last and wins.
                        .order_by(
                            raw.mandate.c.mandate_start, raw.mandate.c.mandate_end.nulls_last()
                        )
                    )
                )
                .mappings()
                .all()
            )
        by_deputy: dict[str, list[dict]] = {}
        for m in mandates:
            by_deputy.setdefault(m["deputy_uid"], []).append(dict(m))
        return [(dict(d), by_deputy.get(d["uid"], [])) for d in deputies]

    async def _project_one(
        self, connection: AsyncConnection, deputy, mandates, legislature_id: int, group_ids: dict
    ) -> bool:
        # The latest seat gives the constituency shown on the card.
        row = deputy_row(deputy, mandates[-1])
        row["slug"] = await unique_slug(connection, pub.deputy, row["slug"], row["external_id"])
        deputy_id, created = await _upsert_by_external_id(
            connection, pub.deputy, row, write_once=("slug",)
        )

        # Mandate needs a group and a start date: both NOT NULL in public.
        for mandate in mandates:
            if mandate["group_uid"] not in group_ids or not mandate["mandate_start"]:
                continue
            row = mandate_row(
                mandate,
                deputy_id=deputy_id,
                legislature_id=legislature_id,
                political_group_id=group_ids[mandate["group_uid"]],
            )
            await connection.execute(
                insert(pub.deputy_mandate)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["deputy_id", "legislature_id", "started_at"],
                    set_={
                        "political_group_id": row["political_group_id"],
                        "ended_at": row["ended_at"],
                    },
                )
            )
        return created
