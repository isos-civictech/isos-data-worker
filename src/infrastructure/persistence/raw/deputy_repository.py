"""
Deputy persistence in `raw`. One transaction per deputy: the deputy, its
mandates and its audit line land together or not at all.
"""
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.ports.repositories.deputy_repository import DeputyRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.mappers.deputy_mapper import (
    deputy_row,
    mandate_row,
    political_group_row,
)

ENTITY = "deputy"


def _upsert(table: sa.Table, row: dict[str, Any], *, key: str, touch_seen: bool = True):
    """Upsert on `key`; `(xmax = 0)` tells an insert from an update."""
    statement = insert(table).values(**row)
    updates = {column: statement.excluded[column] for column in row if column != key}
    if touch_seen:
        updates["last_seen_at"] = sa.func.now()

    return statement.on_conflict_do_update(
        index_elements=[key],
        set_=updates,
    ).returning(table.c.id, (sa.column("xmax") == 0).label("created"))


class SqlRawDeputyRepository(DeputyRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(
        self,
        deputy: Deputy,
        *,
        legislature: int,
        run_id: int,
        source_url: str | None = None,
        checksum: str | None = None,
    ) -> SaveOutcome:
        async with transaction(self._engine) as connection:
            outcome = await self._save_deputy(
                connection, deputy, legislature=legislature, checksum=checksum
            )
            # Same transaction as the deputy.
            await connection.execute(
                sa.insert(tables.ingestion_log).values(
                    run_id=run_id,
                    entity_type=ENTITY,
                    entity_uid=deputy.uid,
                    source_url=source_url,
                    checksum=checksum,
                )
            )
        return outcome

    async def save_political_groups(self, groups: list[PoliticalGroupRef]) -> int:
        if not groups:
            return 0
        async with transaction(self._engine) as connection:
            for group in groups:
                await connection.execute(
                    _upsert(tables.political_group, political_group_row(group), key="uid")
                )
        return len(groups)

    async def _save_deputy(
        self,
        connection: AsyncConnection,
        deputy: Deputy,
        *,
        legislature: int,
        checksum: str | None,
    ) -> SaveOutcome:
        result = await connection.execute(
            _upsert(
                tables.deputy,
                deputy_row(deputy, legislature=legislature, checksum=checksum),
                key="uid",
            )
        )
        deputy_id, created = result.one()

        for mandate in deputy.mandates:
            await connection.execute(
                _upsert(tables.mandate, mandate_row(mandate), key="uid", touch_seen=False)
            )

        return SaveOutcome(entity_id=deputy_id, created=created)
