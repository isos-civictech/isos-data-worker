"""
Purge of `raw` rows that are already in `public` and cannot change any more.

Kept on purpose: scrutins themselves, and amendments examined in séance (`AN`):
the ballot projection matches scrutins to them. The archives in S3 stay, so
anything removed here can be collected again.
"""

from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.ports.repositories.raw_purge import RawPurge

PROJECTED_BALLOT = """
    b.date < :before
    AND EXISTS (
        SELECT 1 FROM public.deputy_vote dv
        JOIN public.ballot p ON p.id = dv.ballot_id
        WHERE p.external_id = b.uid
    )
"""

SELECTS = {
    "ballot_vote": f"""
        SELECT v.id FROM raw.ballot_vote v
        JOIN raw.ballot b ON b.uid = v.ballot_uid
        WHERE {PROJECTED_BALLOT}
    """,
    "ballot_group": f"""
        SELECT g.id FROM raw.ballot_group g
        JOIN raw.ballot b ON b.uid = g.ballot_uid
        WHERE {PROJECTED_BALLOT}
    """,
    "amendment": """
        SELECT a.id FROM raw.amendment a
        WHERE a.deposited_at < :before
          AND a.examined_by IS DISTINCT FROM 'AN'
          AND (a.sort IS NOT NULL OR a.state LIKE 'Irrecevable%' OR a.state IN ('Retiré', 'effacé'))
          AND EXISTS (SELECT 1 FROM public.amendment p WHERE p.external_id = a.uid)
    """,
}


class SqlRawPurge(RawPurge):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def purge(self, before: date, *, dry_run: bool = False) -> dict[str, int]:
        counts: dict[str, int] = {}
        async with self._engine.begin() as connection:
            for table, select in SELECTS.items():
                if dry_run:
                    statement = f"SELECT count(*) FROM ({select}) AS doomed"
                    counts[table] = (
                        await connection.execute(sa.text(statement), {"before": before})
                    ).scalar() or 0
                else:
                    statement = f"DELETE FROM raw.{table} WHERE id IN ({select})"
                    counts[table] = (
                        await connection.execute(sa.text(statement), {"before": before})
                    ).rowcount
        return counts
