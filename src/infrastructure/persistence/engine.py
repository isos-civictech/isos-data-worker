"""
Database engine and transaction boundary.

`transaction()` is the only way the code opens a transaction, and use cases call
it ONCE PER ROOT ENTITY — one deputy and its mandates, one law and its stages,
one sitting with its points and speeches.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


def create_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=5,
        max_overflow=0,
        pool_pre_ping=True,
    )


@asynccontextmanager
async def transaction(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """Commit on success, roll back on any exception."""
    async with engine.begin() as connection:
        yield connection
