"""Add scrape_runs table for tracking scheduled scrape executions."""

import sqlalchemy as sa

from alembic import op

revision = "0003_scrape_runs"
down_revision = "0002_improve_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.Text(), server_default="scheduler", nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_fetched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("new_jobs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("already_exists", sa.Integer(), server_default="0", nullable=False),
        sa.Column("succeeded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed", sa.Text(), server_default="", nullable=False),
        sa.Column("by_source", sa.Text(), server_default="{}", nullable=False),
        sa.Column("by_source_failed", sa.Text(), server_default="{}", nullable=False),
        sa.Column("notified", sa.Text(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scrape_runs"),
    )
    op.create_index("ix_scrape_runs_started_at", "scrape_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_scrape_runs_started_at", table_name="scrape_runs")
    op.drop_table("scrape_runs")
