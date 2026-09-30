"""agenda_item and agenda_point

Revision ID: 2ac502cf62a5
Revises: 0f0775dcbcbd
Create Date: 2026-09-21 03:37:19.259060

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2ac502cf62a5"
down_revision: str | Sequence[str] | None = "0f0775dcbcbd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agenda_item",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("uid", sa.String(length=100), nullable=False),
        sa.Column("legislature", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column("compte_rendu_uid", sa.String(length=100), nullable=True),
        sa.Column("session_rank", sa.String(length=20), nullable=True),
        sa.Column("session_number", sa.Integer(), nullable=True),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["raw.ingestion_run.id"],
            name=op.f("fk_agenda_item_ingestion_run_id"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agenda_item")),
        sa.UniqueConstraint("uid", name=op.f("uq_agenda_item_uid")),
        schema="raw",
    )
    op.create_index(
        "ix_raw_agenda_item_cr", "agenda_item", ["compte_rendu_uid"], unique=False, schema="raw"
    )
    op.create_index(
        "ix_raw_agenda_item_start", "agenda_item", ["start_at"], unique=False, schema="raw"
    )
    op.create_table(
        "agenda_point",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("agenda_uid", sa.String(length=100), nullable=False),
        sa.Column("point_uid", sa.String(length=100), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dossier_refs", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(
            ["agenda_uid"],
            ["raw.agenda_item.uid"],
            name=op.f("fk_agenda_point_agenda_uid"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agenda_point")),
        sa.UniqueConstraint("point_uid", name=op.f("uq_agenda_point_point_uid")),
        schema="raw",
    )
    op.create_index(
        "ix_raw_agenda_point_agenda", "agenda_point", ["agenda_uid"], unique=False, schema="raw"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_raw_agenda_point_agenda", table_name="agenda_point", schema="raw")
    op.drop_table("agenda_point", schema="raw")
    op.drop_index("ix_raw_agenda_item_start", table_name="agenda_item", schema="raw")
    op.drop_index("ix_raw_agenda_item_cr", table_name="agenda_item", schema="raw")
    op.drop_table("agenda_item", schema="raw")
