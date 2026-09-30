"""
raw -> public projection for comptes rendus: enrich the sitting's public.debate row.

The row normally already exists, created by the agenda projection and keyed by
the agenda uid; it is found through raw.agenda_item.compte_rendu_uid. A compte
rendu with no agenda entry (a handful) gets its own row keyed by its own uid.

debate_law is not written here: agenda points carry dossier uids, so the join
becomes possible once laws are collected.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.ports.projections.debate_projection import DebateProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.debate_mapper import debate_row
from src.infrastructure.persistence.serving.slug import unique_slug

WRITE_ONCE = ("slug",)


class SqlDebateProjection(DebateProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="debate-projection")

        async with self._engine.connect() as connection:
            # Each compte rendu with its agenda uid when one references it.
            # A compte rendu may be referenced twice (split sittings): keep the
            # earliest confirmed entry.
            agenda_uid = (
                sa.select(raw.agenda_item.c.uid)
                .where(raw.agenda_item.c.compte_rendu_uid == raw.debate.c.uid)
                .order_by((raw.agenda_item.c.state == "Supprimé").asc(), raw.agenda_item.c.start_at)
                .limit(1)
                .scalar_subquery()
            )
            rows = (
                (
                    await connection.execute(
                        sa.select(raw.debate, agenda_uid.label("agenda_uid"))
                        .where(raw.debate.c.legislature == legislature)
                        .order_by(raw.debate.c.date)
                    )
                )
                .mappings()
                .all()
            )

        for sitting in rows:
            report.processed += 1
            row = debate_row(dict(sitting))
            row["external_id"] = sitting["agenda_uid"] or sitting["uid"]
            async with transaction(self._engine) as connection:
                row["slug"] = await unique_slug(
                    connection, pub.debate, row["slug"], row["external_id"]
                )
                statement = (
                    insert(pub.debate)
                    .values(**row)
                    .on_conflict_do_update(
                        index_elements=["external_id"],
                        set_={k: v for k, v in row.items() if k not in WRITE_ONCE}
                        | {"updated_at": sa.func.now()},
                    )
                    .returning(pub.debate.c.id, (sa.column("xmax") == 0).label("created"))
                )
                _, created = (await connection.execute(statement)).one()
            report.created += int(created)
            report.updated += int(not created)

        return report.finish()
