"""debate points: kind, level, parent; natural keys

Revision ID: 99eccad16801
Revises: 4f5258762eca
Create Date: 2026-09-20 23:14:36.828011

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "99eccad16801"
down_revision: str | Sequence[str] | None = "4f5258762eca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("debate", sa.Column("title", sa.Text(), nullable=True), schema="raw")
    op.add_column(
        "debate_point", sa.Column("parent_uid", sa.String(length=100), nullable=True), schema="raw"
    )
    op.add_column(
        "debate_point", sa.Column("kind", sa.String(length=50), nullable=True), schema="raw"
    )
    op.add_column(
        "debate_point",
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        schema="raw",
    )
    op.alter_column(
        "debate_point",
        "point_uid",
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
        schema="raw",
    )
    op.create_unique_constraint(
        op.f("uq_debate_point_point_uid"), "debate_point", ["point_uid"], schema="raw"
    )
    op.alter_column(
        "intervention", "uid", existing_type=sa.VARCHAR(length=100), nullable=False, schema="raw"
    )
    op.create_unique_constraint(op.f("uq_intervention_uid"), "intervention", ["uid"], schema="raw")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("uq_intervention_uid"), "intervention", schema="raw", type_="unique")
    op.alter_column(
        "intervention", "uid", existing_type=sa.VARCHAR(length=100), nullable=True, schema="raw"
    )
    op.drop_constraint(
        op.f("uq_debate_point_point_uid"), "debate_point", schema="raw", type_="unique"
    )
    op.alter_column(
        "debate_point",
        "point_uid",
        existing_type=sa.VARCHAR(length=100),
        nullable=True,
        schema="raw",
    )
    op.drop_column("debate_point", "level", schema="raw")
    op.drop_column("debate_point", "kind", schema="raw")
    op.drop_column("debate_point", "parent_uid", schema="raw")
    op.drop_column("debate", "title", schema="raw")
