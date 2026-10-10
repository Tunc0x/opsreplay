"""add persistent postmortem drafts

Revision ID: 94a3c9842e5b
Revises: 1b5260e0732c
Create Date: 2026-10-10 11:25:30.613442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '94a3c9842e5b'
down_revision: Union[str, Sequence[str], None] = '1b5260e0732c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "postmortem_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
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
            ["incident_id"],
            ["incidents.id"],
            name="fk_postmortem_drafts_incident_id_incidents",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            name="uq_postmortem_drafts_incident_id",
        ),
    )
    op.create_table(
        "postmortem_draft_evidence",
        sa.Column("postmortem_draft_id", sa.Integer(), nullable=False),
        sa.Column("timeline_event_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["postmortem_draft_id"],
            ["postmortem_drafts.id"],
            name=(
                "fk_postmortem_draft_evidence_draft_id_"
                "postmortem_drafts"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["timeline_event_id"],
            ["timeline_events.id"],
            name=(
                "fk_postmortem_draft_evidence_event_id_"
                "timeline_events"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "postmortem_draft_id",
            "timeline_event_id",
        ),
        sa.UniqueConstraint(
            "postmortem_draft_id",
            "position",
            name="uq_postmortem_draft_evidence_draft_position",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("postmortem_draft_evidence")
    op.drop_table("postmortem_drafts")
