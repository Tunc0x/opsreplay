"""add incidents

Revision ID: ae7975debb3b
Revises: eecb494d05c8
Create Date: 2026-10-04 10:13:59.204434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae7975debb3b'
down_revision: Union[str, Sequence[str], None] = 'eecb494d05c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("trigger_timeline_event_id", sa.Integer(), nullable=False),
        sa.Column("lookback_minutes", sa.Integer(), nullable=False),
        sa.Column("lookahead_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "lookback_minutes >= 0 AND lookback_minutes <= 1440",
            name="ck_incidents_lookback_minutes_range",
        ),
        sa.CheckConstraint(
            "lookahead_minutes >= 0 AND lookahead_minutes <= 1440",
            name="ck_incidents_lookahead_minutes_range",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_incidents_repository_id_repositories",
        ),
        sa.ForeignKeyConstraint(
            ["trigger_timeline_event_id"],
            ["timeline_events.id"],
            name=(
                "fk_incidents_trigger_timeline_event_id_"
                "timeline_events"
            ),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trigger_timeline_event_id",
            name="uq_incidents_trigger_timeline_event_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("incidents")
