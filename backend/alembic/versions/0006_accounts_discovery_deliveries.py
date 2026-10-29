"""Private accounts, cached discovery scores and durable notification deliveries.

Existing private rows belong to a disabled legacy account. Only an explicit
operator command can transfer them to an account; registration never claims data.
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_accounts"
down_revision = "0005_application_statuses"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column(name, sa.DateTime(), server_default=sa.func.now(), nullable=False)
        for name in ("created_at", "updated_at")
    ]


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.Text(), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("profile", sa.Text(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.execute(
        "INSERT INTO users (id,email,is_active,is_admin,profile,profile_version) "
        "VALUES (1,'legacy@jobhunter.invalid',false,false,'{}',1)"
    )
    op.execute("SELECT setval(pg_get_serial_sequence('users','id'), 1)")
    op.create_table(
        "login_sessions",
        sa.Column("token_hash", sa.Text(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_login_sessions_user_id", "login_sessions", ["user_id"])
    op.create_index("ix_login_sessions_expires_at", "login_sessions", ["expires_at"])
    for table in ("saved_jobs", "applications"):
        op.add_column(table, sa.Column("user_id", sa.Integer(), server_default="1", nullable=False))
        op.create_foreign_key(
            f"fk_{table}_user_id_users", table, "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        op.drop_constraint(f"uq_{table}_job_id", table, type_="unique")
        op.create_unique_constraint(f"uq_{table}_user_id", table, ["user_id", "job_id"])
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.alter_column(table, "user_id", server_default=None)
    op.create_table(
        "candidate_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("job_updated_at", sa.DateTime(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("eligibility", sa.Text(), nullable=False),
        sa.Column("employment_type", sa.Text(), nullable=False),
        sa.UniqueConstraint("user_id", "job_id"),
        *_timestamps(),
    )
    for name in ("user_id", "job_id", "score"):
        op.create_index(f"ix_candidate_scores_{name}", "candidate_scores", [name])
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime()),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("job_id", "channel"),
        *_timestamps(),
    )
    for name in ("job_id", "status"):
        op.create_index(f"ix_notification_deliveries_{name}", "notification_deliveries", [name])


def downgrade():
    # Multiple users may own the same job; silently collapsing those rows loses data.
    raise RuntimeError("Account migration requires an explicit data export before rollback.")
