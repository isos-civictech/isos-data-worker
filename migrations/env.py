"""
Alembic for the `raw` schema.

  * `include_object` rejects anything outside `raw`.
  * `version_table_schema="raw"` puts our `alembic_version` table inside our own
    schema, so the two migration histories never collide.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config import get_settings
from src.infrastructure.persistence.raw.tables import SCHEMA, metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


config.set_main_option("sqlalchemy.url", get_settings().database_url)


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    """Keep autogenerate strictly inside `raw`."""
    if type_ == "table":
        return object_.schema == SCHEMA
    # Indexes, constraints and columns follow the table they belong to.
    if hasattr(object_, "table") and object_.table is not None:
        return object_.table.schema == SCHEMA
    return True


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,
        version_table_schema=SCHEMA,
        compare_type=True,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
