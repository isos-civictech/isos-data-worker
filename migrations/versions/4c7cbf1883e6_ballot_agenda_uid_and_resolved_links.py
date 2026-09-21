"""ballot agenda_uid and resolved links

Revision ID: 4c7cbf1883e6
Revises: 7e8ab396d72c
Create Date: 2026-09-21 11:41:12.641197

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c7cbf1883e6"
down_revision: str | Sequence[str] | None = "7e8ab396d72c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("ballot", "sitting_uid", new_column_name="agenda_uid", schema="raw")
    op.execute("ALTER INDEX raw.ix_raw_ballot_sitting RENAME TO ix_raw_ballot_agenda")
    op.add_column("ballot", sa.Column("resolved_dossier_uid", sa.String(length=100)), schema="raw")
    op.add_column(
        "ballot", sa.Column("resolved_amendment_uid", sa.String(length=100)), schema="raw"
    )
    op.create_index(
        "ix_raw_ballot_resolved_dossier", "ballot", ["resolved_dossier_uid"], schema="raw"
    )
    op.create_index(
        "ix_raw_ballot_resolved_amendment", "ballot", ["resolved_amendment_uid"], schema="raw"
    )


def downgrade() -> None:
    op.drop_index("ix_raw_ballot_resolved_amendment", table_name="ballot", schema="raw")
    op.drop_index("ix_raw_ballot_resolved_dossier", table_name="ballot", schema="raw")
    op.drop_column("ballot", "resolved_amendment_uid", schema="raw")
    op.drop_column("ballot", "resolved_dossier_uid", schema="raw")
    op.execute("ALTER INDEX raw.ix_raw_ballot_agenda RENAME TO ix_raw_ballot_sitting")
    op.alter_column("ballot", "agenda_uid", new_column_name="sitting_uid", schema="raw")
