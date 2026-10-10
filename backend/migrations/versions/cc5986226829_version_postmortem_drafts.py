"""version postmortem drafts

Revision ID: cc5986226829
Revises: 94a3c9842e5b
Create Date: 2026-10-10 15:17:56.132825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc5986226829'
down_revision: Union[str, Sequence[str], None] = '94a3c9842e5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "postmortem_drafts",
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.alter_column(
        "postmortem_drafts",
        "version",
        server_default=None,
    )
    op.drop_constraint(
        "uq_postmortem_drafts_incident_id",
        "postmortem_drafts",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_postmortem_drafts_incident_version",
        "postmortem_drafts",
        ["incident_id", "version"],
    )
    op.create_check_constraint(
        "ck_postmortem_drafts_version_positive",
        "postmortem_drafts",
        "version >= 1",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DELETE FROM postmortem_draft_evidence
            WHERE postmortem_draft_id IN (
                SELECT id
                FROM postmortem_drafts
                WHERE version > 1
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM postmortem_drafts
            WHERE version > 1
            """
        )
    )
    op.drop_constraint(
        "ck_postmortem_drafts_version_positive",
        "postmortem_drafts",
        type_="check",
    )
    op.drop_constraint(
        "uq_postmortem_drafts_incident_version",
        "postmortem_drafts",
        type_="unique",
    )
    op.drop_column("postmortem_drafts", "version")
    op.create_unique_constraint(
        "uq_postmortem_drafts_incident_id",
        "postmortem_drafts",
        ["incident_id"],
    )
