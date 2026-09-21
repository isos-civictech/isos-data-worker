"""
raw -> public projection for amendments, by pages of 1 000.

The lookups (law, deputy, group, reading) are loaded once into memory:
125 000 rows times four queries would take an hour.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.ports.projections.amendment_projection import AmendmentProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.amendment_mapper import (
    amendment_from_raw,
    amendment_row,
)
from src.infrastructure.persistence.serving.mappers.law_mapper import READINGS

PAGE = 1000


class SqlAmendmentProjection(AmendmentProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="amendment-projection")

        async with self._engine.connect() as connection:
            laws = await self._map(connection, pub.law.c.external_id, pub.law.c.id)
            deputies = await self._map(connection, pub.deputy.c.external_id, pub.deputy.c.id)
            groups = await self._map(
                connection, pub.political_group.c.external_id, pub.political_group.c.id
            )
            readings = await self._readings(connection)

        last_id = 0
        while True:
            async with transaction(self._engine) as connection:
                page = (
                    (
                        await connection.execute(
                            sa.select(raw.amendment)
                            .where(
                                raw.amendment.c.legislature == legislature,
                                raw.amendment.c.id > last_id,
                            )
                            .order_by(raw.amendment.c.id)
                            .limit(PAGE)
                        )
                    )
                    .mappings()
                    .all()
                )
                if not page:
                    break
                last_id = page[-1]["id"]
                rows = []
                for r in page:
                    report.processed += 1
                    a = amendment_from_raw(dict(r))
                    law_id = laws.get(a.dossier_uid)
                    deputy_id = deputies.get(a.deputy_uid)
                    if law_id is None or (a.author_type.value == "Député" and deputy_id is None):
                        # Not a law (résolution…), or a deputy we do not know.
                        report.skipped += 1
                        continue
                    rows.append(
                        amendment_row(
                            a,
                            law_id=law_id,
                            deputy_id=deputy_id,
                            group_id=groups.get(a.group_uid),
                            reading_id=readings.get((law_id, a.texte_uid)),
                        )
                    )
                if rows:
                    created = await self._upsert(connection, rows)
                    report.created += created
                    report.updated += len(rows) - created

        return report.finish()

    @staticmethod
    async def _map(connection: AsyncConnection, key, value) -> dict:
        return dict((await connection.execute(sa.select(key, value).where(key.isnot(None)))).all())

    @staticmethod
    async def _readings(connection: AsyncConnection) -> dict[tuple[int, str], int]:
        """
        (public law id, texte uid) -> law_reading id. Commission amendments target
        the deposited text, séance amendments the commission's text: both map.
        """
        stage, reading, law = raw.law_stage, pub.law_reading, pub.law
        reading_ids = {
            (law_id, chamber, number): rid
            for rid, law_id, chamber, number in (
                await connection.execute(
                    sa.select(
                        reading.c.id,
                        reading.c.law_id,
                        # Enum column declared without values: read it as text.
                        sa.cast(reading.c.chamber, sa.Text),
                        reading.c.reading_number,
                    )
                )
            ).all()
        }
        stages = (
            await connection.execute(
                sa.select(law.c.id, stage.c.texte_uid, stage.c.commission_texte_uid, stage.c.code)
                .select_from(stage)
                .join(law, law.c.external_id == stage.c.dossier_uid)
            )
        ).all()
        out = {}
        for law_id, texte_uid, commission_texte_uid, code in stages:
            if code not in READINGS:
                continue
            rid = reading_ids.get((law_id, *READINGS[code]))
            if rid is None:
                continue
            for uid in (texte_uid, commission_texte_uid):
                if uid:
                    out[(law_id, uid)] = rid
        return out

    @staticmethod
    async def _upsert(connection: AsyncConnection, rows: list[dict]) -> int:
        statement = insert(pub.amendment).values(rows)
        updates = {c: statement.excluded[c] for c in rows[0] if c != "external_id"}
        updates["updated_at"] = sa.func.now()
        flags = (
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["external_id"], set_=updates
                ).returning((sa.column("xmax") == 0).label("created"))
            )
        ).scalars()
        return sum(flags)
