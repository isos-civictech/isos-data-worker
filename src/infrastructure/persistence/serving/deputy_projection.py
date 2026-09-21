"""
raw -> public projection for deputies.

`public.deputy` and `public.political_group` have no unique index on
external_id, so the upsert is a lookup then insert-or-update rather than
ON CONFLICT. Slugs are written once and never updated: a title fix upstream
must not break an already-indexed URL.
"""

from datetime import date

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.ports.projections.deputy_projection import DeputyProjection
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

# The 17th legislature opened on 2024-07-18; earlier ones are not collected.
LEGISLATURE_START = {17: date(2024, 7, 18)}


async def ensure_legislature(connection: AsyncConnection, number: int) -> int:
    """
    ON CONFLICT DO UPDATE with a no-op set: DO NOTHING returns no row on
    conflict, and we need the id either way.
    """
    statement = (
        insert(pub.legislature)
        .values(number=number, started_at=LEGISLATURE_START.get(number, date(2024, 7, 18)))
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

        for deputy, mandate in raw_deputies:
            report.processed += 1
            try:
                async with transaction(self._engine) as connection:
                    created = await self._project_one(
                        connection, deputy, mandate, legislature_id, group_ids
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

    async def _load_raw_deputies(self, legislature: int) -> list[tuple]:
        """Each deputy with its (single, current) mandate — None if absent."""
        query = (
            sa.select(raw.deputy, raw.mandate)
            .select_from(
                raw.deputy.outerjoin(raw.mandate, raw.mandate.c.deputy_uid == raw.deputy.c.uid)
            )
            .where(raw.deputy.c.legislature == legislature)
            .order_by(raw.deputy.c.uid)
        )
        async with self._engine.connect() as connection:
            result = await connection.execute(query)
            pairs = []
            for row in result.mappings():
                deputy = {c.name: row[c] for c in raw.deputy.c}
                mandate = {c.name: row[c] for c in raw.mandate.c} if row[raw.mandate.c.id] else None
                pairs.append((deputy, mandate))
        return pairs

    async def _project_one(
        self, connection: AsyncConnection, deputy, mandate, legislature_id: int, group_ids: dict
    ) -> bool:
        row = deputy_row(deputy, mandate)
        row["slug"] = await unique_slug(connection, pub.deputy, row["slug"], row["external_id"])
        deputy_id, created = await _upsert_by_external_id(
            connection, pub.deputy, row, write_once=("slug",)
        )

        # Mandate needs a group and a start date: both NOT NULL in public.
        if mandate and mandate["group_uid"] in group_ids and mandate["mandate_start"]:
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
