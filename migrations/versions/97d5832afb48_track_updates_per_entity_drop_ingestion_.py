"""track updates per entity, drop ingestion_log

Per-run tracking moves to ingestion_run (s3_key). Per-entity rows get
updated_at (content changed) and last_run_id. No per-entity checksum: Postgres
compares columns at upsert time instead.

Revision ID: 97d5832afb48
Revises: a6b93df75ec7
Create Date: 2026-09-18 09:57:08.714296

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "97d5832afb48"
down_revision: str | Sequence[str] | None = "a6b93df75ec7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_raw_ingestion_log_entity"), table_name="ingestion_log", schema="raw")
    op.drop_table("ingestion_log", schema="raw")
    op.add_column("debate", sa.Column("last_run_id", sa.BigInteger(), nullable=True), schema="raw")
    op.add_column(
        "debate",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="raw",
    )
    op.create_foreign_key(
        op.f("fk_debate_last_run_id"),
        "debate",
        "ingestion_run",
        ["last_run_id"],
        ["id"],
        source_schema="raw",
        referent_schema="raw",
        ondelete="SET NULL",
    )
    op.drop_column("debate", "checksum", schema="raw")
    op.add_column("deputy", sa.Column("last_run_id", sa.BigInteger(), nullable=True), schema="raw")
    op.add_column(
        "deputy",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="raw",
    )
    op.create_foreign_key(
        op.f("fk_deputy_last_run_id"),
        "deputy",
        "ingestion_run",
        ["last_run_id"],
        ["id"],
        source_schema="raw",
        referent_schema="raw",
        ondelete="SET NULL",
    )
    op.drop_column("deputy", "checksum", schema="raw")
    op.add_column("ingestion_run", sa.Column("s3_key", sa.Text(), nullable=True), schema="raw")
    op.add_column("law", sa.Column("last_run_id", sa.BigInteger(), nullable=True), schema="raw")
    op.add_column(
        "law",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="raw",
    )
    op.create_foreign_key(
        op.f("fk_law_last_run_id"),
        "law",
        "ingestion_run",
        ["last_run_id"],
        ["id"],
        source_schema="raw",
        referent_schema="raw",
        ondelete="SET NULL",
    )
    op.drop_column("law", "checksum", schema="raw")
    op.drop_column("mandate", "group_acronym", schema="raw")
    op.drop_column("mandate", "group_name", schema="raw")
    op.add_column("political_group", sa.Column("s3_key", sa.Text(), nullable=True), schema="raw")
    op.add_column(
        "political_group", sa.Column("last_run_id", sa.BigInteger(), nullable=True), schema="raw"
    )
    op.add_column(
        "political_group",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="raw",
    )
    op.create_foreign_key(
        op.f("fk_political_group_last_run_id"),
        "political_group",
        "ingestion_run",
        ["last_run_id"],
        ["id"],
        source_schema="raw",
        referent_schema="raw",
        ondelete="SET NULL",
    )
    op.drop_column("political_group", "checksum", schema="raw")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "political_group",
        sa.Column("checksum", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        schema="raw",
    )
    op.drop_constraint(
        op.f("fk_political_group_last_run_id"), "political_group", schema="raw", type_="foreignkey"
    )
    op.drop_column("political_group", "updated_at", schema="raw")
    op.drop_column("political_group", "last_run_id", schema="raw")
    op.drop_column("political_group", "s3_key", schema="raw")
    op.add_column(
        "mandate",
        sa.Column("group_name", sa.TEXT(), autoincrement=False, nullable=True),
        schema="raw",
    )
    op.add_column(
        "mandate",
        sa.Column("group_acronym", sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        schema="raw",
    )
    op.add_column(
        "law",
        sa.Column("checksum", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        schema="raw",
    )
    op.drop_constraint(op.f("fk_law_last_run_id"), "law", schema="raw", type_="foreignkey")
    op.drop_column("law", "updated_at", schema="raw")
    op.drop_column("law", "last_run_id", schema="raw")
    op.drop_column("ingestion_run", "s3_key", schema="raw")
    op.add_column(
        "deputy",
        sa.Column("checksum", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        schema="raw",
    )
    op.drop_constraint(op.f("fk_deputy_last_run_id"), "deputy", schema="raw", type_="foreignkey")
    op.drop_column("deputy", "updated_at", schema="raw")
    op.drop_column("deputy", "last_run_id", schema="raw")
    op.add_column(
        "debate",
        sa.Column("checksum", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        schema="raw",
    )
    op.drop_constraint(op.f("fk_debate_last_run_id"), "debate", schema="raw", type_="foreignkey")
    op.drop_column("debate", "updated_at", schema="raw")
    op.drop_column("debate", "last_run_id", schema="raw")
    op.create_table(
        "ingestion_log",
        sa.Column("id", sa.BIGINT(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BIGINT(), autoincrement=False, nullable=False),
        sa.Column("entity_type", sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column("entity_uid", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column("source_url", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("s3_key", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("checksum", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        sa.Column(
            "fetched_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["raw.ingestion_run.id"],
            name=op.f("fk_ingestion_log_run_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_log")),
        schema="raw",
    )
    op.create_index(
        op.f("ix_raw_ingestion_log_entity"),
        "ingestion_log",
        ["entity_type", "entity_uid"],
        unique=False,
        schema="raw",
    )
