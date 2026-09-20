"""rename tracking columns, drop last_seen_at

first_seen_at -> created_at, last_run_id -> ingestion_run_id. last_seen_at is
dropped: it duplicated ingestion_run.finished_at reachable through the FK.

Hand-written: autogenerate turns a rename into drop + add and loses the data.

Revision ID: 4f5258762eca
Revises: 97d5832afb48
Create Date: 2026-09-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4f5258762eca"
down_revision: str | Sequence[str] | None = "97d5832afb48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "raw"
TABLES = ("political_group", "deputy", "law", "debate")


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "first_seen_at", new_column_name="created_at", schema=SCHEMA)
        op.alter_column(table, "last_run_id", new_column_name="ingestion_run_id", schema=SCHEMA)
        op.drop_column(table, "last_seen_at", schema=SCHEMA)
        # The FK keeps its old name otherwise; keep it aligned with the convention.
        op.drop_constraint(f"fk_{table}_last_run_id", table, schema=SCHEMA, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{table}_ingestion_run_id",
            table,
            "ingestion_run",
            ["ingestion_run_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
            ondelete="SET NULL",
        )


def downgrade() -> None:
    import sqlalchemy as sa

    for table in TABLES:
        op.drop_constraint(f"fk_{table}_ingestion_run_id", table, schema=SCHEMA, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{table}_last_run_id",
            table,
            "ingestion_run",
            ["ingestion_run_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
            ondelete="SET NULL",
        )
        op.add_column(
            table,
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema=SCHEMA,
        )
        op.alter_column(table, "ingestion_run_id", new_column_name="last_run_id", schema=SCHEMA)
        op.alter_column(table, "created_at", new_column_name="first_seen_at", schema=SCHEMA)
