"""debate_point: drop level, parent_uid is the tree

Revision ID: 0f0775dcbcbd
Revises: 99eccad16801
Create Date: 2026-09-21 03:09:21.650121

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f0775dcbcbd"
down_revision: str | Sequence[str] | None = "99eccad16801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("debate_point", "level", schema="raw")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "debate_point",
        sa.Column(
            "level", sa.INTEGER(), server_default=sa.text("1"), autoincrement=False, nullable=False
        ),
        schema="raw",
    )
