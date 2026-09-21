"""amendment signatories as names

Revision ID: 279a47116401
Revises: 058a2d0e6411
Create Date: 2026-09-21 09:39:17.291840

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "279a47116401"
down_revision: str | Sequence[str] | None = "058a2d0e6411"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE raw.amendment ALTER COLUMN signatories TYPE TEXT[] "
        "USING CASE WHEN signatories IS NULL THEN '{}' ELSE ARRAY[signatories] END, "
        "ALTER COLUMN signatories SET DEFAULT '{}', ALTER COLUMN signatories SET NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE raw.amendment ALTER COLUMN signatories DROP NOT NULL, "
        "ALTER COLUMN signatories DROP DEFAULT, "
        "ALTER COLUMN signatories TYPE TEXT USING array_to_string(signatories, ', ')"
    )
