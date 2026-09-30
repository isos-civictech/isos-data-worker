"""Opening day of each legislature (the AN publishes no such table)."""

from datetime import date, timedelta

LEGISLATURE_START = {
    17: date(2024, 7, 18),
    16: date(2022, 6, 22),
    15: date(2017, 6, 21),
    14: date(2012, 6, 20),
    13: date(2007, 6, 20),
    12: date(2002, 6, 19),
    11: date(1997, 6, 12),
    10: date(1993, 4, 2),
    9: date(1988, 6, 23),
    8: date(1986, 4, 2),
}


def legislature_start(number: int) -> date:
    return LEGISLATURE_START.get(number, LEGISLATURE_START[max(LEGISLATURE_START)])


def legislature_end(number: int) -> date | None:
    """Day before the next one opened; None while the legislature is running."""
    following = LEGISLATURE_START.get(number + 1)
    return following - timedelta(days=1) if following else None
