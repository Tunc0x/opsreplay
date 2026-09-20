"""add webhook processed timestamp

Revision ID: c7a6d5cdb61d
Revises: cf2347aed0e8
Create Date: 2026-09-19 23:43:45.652373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a6d5cdb61d'
down_revision: Union[str, Sequence[str], None] = 'cf2347aed0e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "webhook_deliveries",
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("webhook_deliveries", "processed_at")
