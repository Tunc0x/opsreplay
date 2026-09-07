"""add GitHub repository identity

Revision ID: c774afb9c4b8
Revises: 726aa48eabc3
Create Date: 2026-09-07 13:46:55.290605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c774afb9c4b8'
down_revision: Union[str, Sequence[str], None] = '726aa48eabc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "repositories",
        sa.Column("github_repository_id", sa.BigInteger(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_repositories_github_repository_id",
        "repositories",
        ["github_repository_id"],
    )
    op.add_column(
        "webhook_deliveries",
        sa.Column("repository_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_webhook_deliveries_repository_id_repositories",
        "webhook_deliveries",
        "repositories",
        ["repository_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_webhook_deliveries_repository_id_repositories",
        "webhook_deliveries",
        type_="foreignkey",
    )
    op.drop_column("webhook_deliveries", "repository_id")
    op.drop_constraint(
        "uq_repositories_github_repository_id",
        "repositories",
        type_="unique",
    )
    op.drop_column("repositories", "github_repository_id")
