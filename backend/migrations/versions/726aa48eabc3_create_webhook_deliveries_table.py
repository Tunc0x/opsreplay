"""create webhook deliveries table

Revision ID: 726aa48eabc3
Revises: 2d49364e23ce
Create Date: 2026-09-03 16:35:07.501400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '726aa48eabc3'
down_revision: Union[str, Sequence[str], None] = '2d49364e23ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "delivery_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("payload_body", sa.LargeBinary(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "delivery_id",
            name="uq_webhook_deliveries_delivery_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("webhook_deliveries")
