"""
raw -> public.deputy_participation_day: each deputy's attendance, day by day.

Counted on every scrutin of the legislature, not only those whose sitting is
published as a debate. A scrutin counts for a deputy when it falls inside one
of their mandates; it is "voted" when the (corrected) position is pour, contre
or abstention. The API only sums a window of days.
"""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

REFRESH = sa.text(
    """
    WITH seated AS (
        SELECT DISTINCT m.deputy_id, b.uid, b.date
        FROM raw.ballot b
        JOIN public.deputy_mandate m
          ON b.date >= m.started_at AND (m.ended_at IS NULL OR b.date <= m.ended_at)
        WHERE b.legislature = :legislature
    ), positions AS (
        SELECT s.deputy_id, s.date, coalesce(v.corrected_position, v.position) AS position
        FROM seated s
        JOIN public.deputy d ON d.id = s.deputy_id
        LEFT JOIN raw.ballot_vote v ON v.ballot_uid = s.uid AND v.deputy_uid = d.external_id
    )
    INSERT INTO public.deputy_participation_day
        (deputy_id, day, ballots_total, ballots_voted, votes_for, votes_against, abstentions)
    SELECT deputy_id, date, count(*),
           count(*) FILTER (WHERE position IN ('pour', 'contre', 'abstention')),
           count(*) FILTER (WHERE position = 'pour'),
           count(*) FILTER (WHERE position = 'contre'),
           count(*) FILTER (WHERE position = 'abstention')
    FROM positions
    GROUP BY deputy_id, date
    """
)


async def refresh_participation(connection: AsyncConnection, legislature: int) -> int:
    """Rebuild every day of the legislature in one transaction; returns the rows written."""
    await connection.execute(
        sa.text(
            "DELETE FROM public.deputy_participation_day "
            "WHERE day IN (SELECT date FROM raw.ballot WHERE legislature = :legislature)"
        ),
        {"legislature": legislature},
    )
    result = await connection.execute(REFRESH, {"legislature": legislature})
    return result.rowcount
