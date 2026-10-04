"""add incident resolution lifecycle

Revision ID: 1b5260e0732c
Revises: ae7975debb3b
Create Date: 2026-10-04 23:26:59.314796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b5260e0732c'
down_revision: Union[str, Sequence[str], None] = 'ae7975debb3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "incidents",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_incidents_status",
        "incidents",
        "status IN ('open', 'resolved')",
    )
    op.create_check_constraint(
        "ck_incidents_resolution_state",
        "incidents",
        "(status = 'open' AND resolved_at IS NULL) OR "
        "(status = 'resolved' AND resolved_at IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_incidents_resolution_state",
        "incidents",
        type_="check",
    )
    op.drop_constraint(
        "ck_incidents_status",
        "incidents",
        type_="check",
    )
    op.drop_column("incidents", "resolved_at")
    op.drop_column("incidents", "status")
