"""add timeline events

Revision ID: 982d313bef40
Revises: c7a6d5cdb61d
Create Date: 2026-09-20 21:17:09.004690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '982d313bef40'
down_revision: Union[str, Sequence[str], None] = 'c7a6d5cdb61d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("webhook_delivery_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_timeline_events_repository_id_repositories",
        ),
        sa.ForeignKeyConstraint(
            ["webhook_delivery_id"],
            ["webhook_deliveries.id"],
            name=(
                "fk_timeline_events_webhook_delivery_id_"
                "webhook_deliveries"
            ),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "webhook_delivery_id",
            name="uq_timeline_events_webhook_delivery_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("timeline_events")
