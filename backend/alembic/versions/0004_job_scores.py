"""Add job_scores table for persisted deterministic match scores.

Pure additive change: no existing table or column is altered, so current
job data and the other relations are untouched.
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_job_scores"
down_revision = "0003_scrape_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("role_points", sa.Integer(), nullable=False),
        sa.Column("skill_points", sa.Integer(), nullable=False),
        sa.Column("preference_points", sa.Integer(), nullable=False),
        sa.Column("matched_roles", sa.Text(), nullable=False),
        sa.Column("matched_skills", sa.Text(), nullable=False),
        sa.Column("missing_skills", sa.Text(), nullable=False),
        sa.Column("matched_preferences", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_job_scores_job_id_jobs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_scores"),
        sa.UniqueConstraint("job_id", name="uq_job_scores_job_id"),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_job_scores_score_range",
        ),
    )
    op.create_index("ix_job_scores_score", "job_scores", ["score"])


def downgrade() -> None:
    op.drop_index("ix_job_scores_score", table_name="job_scores")
    op.drop_table("job_scores")
