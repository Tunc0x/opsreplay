"""add webhook delivery outbox

Revision ID: cf2347aed0e8
Revises: e8f984888013
Create Date: 2026-09-18 13:23:58.257449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf2347aed0e8'
down_revision: Union[str, Sequence[str], None] = 'e8f984888013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "webhook_delivery_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("webhook_delivery_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["webhook_delivery_id"],
            ["webhook_deliveries.id"],
            name="fk_webhook_delivery_outbox_delivery_id_webhook_deliveries",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "webhook_delivery_id",
            name="uq_webhook_delivery_outbox_webhook_delivery_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("webhook_delivery_outbox")
