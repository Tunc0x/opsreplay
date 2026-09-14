"""add GitHub installation

Revision ID: e8f984888013
Revises: c774afb9c4b8
Create Date: 2026-09-14 18:17:09.799314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f984888013'
down_revision: Union[str, Sequence[str], None] = 'c774afb9c4b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "github_installations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("github_installation_id", sa.BigInteger(), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_github_installations_organization_id_organizations",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            name="uq_github_installations_organization_id",
        ),
        sa.UniqueConstraint(
            "github_installation_id",
            name="uq_github_installations_github_installation_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("github_installations")
