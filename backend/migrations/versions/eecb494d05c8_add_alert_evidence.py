"""add alert evidence

Revision ID: eecb494d05c8
Revises: 982d313bef40
Create Date: 2026-09-28 11:09:03.547618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eecb494d05c8'
down_revision: Union[str, Sequence[str], None] = '982d313bef40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "external_event_id", sa.String(length=200), nullable=False
        ),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("payload_body", sa.LargeBinary(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            name="fk_alert_deliveries_repository_id_repositories",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "external_event_id",
            name="uq_alert_deliveries_external_event_id",
        ),
    )

    op.alter_column(
        "timeline_events",
        "webhook_delivery_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "timeline_events",
        sa.Column("alert_delivery_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_timeline_events_alert_delivery_id_alert_deliveries",
        "timeline_events",
        "alert_deliveries",
        ["alert_delivery_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_timeline_events_alert_delivery_id",
        "timeline_events",
        ["alert_delivery_id"],
    )
    op.create_check_constraint(
        "ck_timeline_events_exactly_one_evidence_source",
        "timeline_events",
        "(webhook_delivery_id IS NOT NULL AND alert_delivery_id IS NULL) "
        "OR (webhook_delivery_id IS NULL AND alert_delivery_id IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM timeline_events WHERE alert_delivery_id IS NOT NULL"
    )
    op.drop_constraint(
        "ck_timeline_events_exactly_one_evidence_source",
        "timeline_events",
        type_="check",
    )
    op.drop_constraint(
        "uq_timeline_events_alert_delivery_id",
        "timeline_events",
        type_="unique",
    )
    op.drop_constraint(
        "fk_timeline_events_alert_delivery_id_alert_deliveries",
        "timeline_events",
        type_="foreignkey",
    )
    op.drop_column("timeline_events", "alert_delivery_id")
    op.alter_column(
        "timeline_events",
        "webhook_delivery_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_table("alert_deliveries")
