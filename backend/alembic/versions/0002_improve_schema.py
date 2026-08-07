"""Improve schema: Sources table, FKs, timestamps, triggers and new entities.

Applies additive changes so existing records in `jobs` are preserved
and backfilled. Existing URLs are kept unique; `sources` are derived
from the distinct values already stored in `jobs.source`.
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_improve_schema"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- sources ----------------
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )

    # Backfill sources from existing data (auto created_at/updated_at handled by defaults).
    op.execute(
        "INSERT INTO sources (name, created_at, updated_at) "
        "SELECT DISTINCT source, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
        "FROM jobs WHERE source IS NOT NULL"
    )

    # ---------------- jobs ----------------
    # Enforce unique url naming + allow more future control.
    op.add_column(
        "jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Backfill updated_at for existing rows.
    op.execute("UPDATE jobs SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)")

    # created_at -> NOT NULL, server default (all existing rows are populated).
    op.alter_column(
        "jobs",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    # FKs + indexes.
    op.create_index("ix_jobs_company", "jobs", ["company"])
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])

    op.create_foreign_key(
        "fk_jobs_source_sources",
        "jobs",
        "sources",
        ["source"],
        ["name"],
        ondelete="RESTRICT",
    )

    # Rename the auto-named url unique constraint for consistency.
    op.execute("ALTER TABLE jobs RENAME CONSTRAINT jobs_url_key TO uq_jobs_url")

    # Constraints.
    op.create_check_constraint("title_not_empty", "jobs", "length(title) > 0")
    op.create_check_constraint("company_not_empty", "jobs", "length(company) > 0")

    # ---------------- applications ----------------
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default="applied",
            nullable=False,
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
        sa.UniqueConstraint("job_id", name="uq_applications_job_id"),
    )
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_foreign_key(
        "fk_applications_job_id_jobs",
        "applications",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "valid_status",
        "applications",
        "status IN ('applied', 'interviewing', 'offer', 'rejected')",
    )

    # ---------------- saved_jobs ----------------
    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "saved_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id", name="pk_saved_jobs"),
        sa.UniqueConstraint("job_id", name="uq_saved_jobs_job_id"),
    )
    op.create_foreign_key(
        "fk_saved_jobs_job_id_jobs",
        "saved_jobs",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ---------------- automatic updated_at ----------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table in ("sources", "jobs", "applications", "saved_jobs"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
            """
        )


def downgrade() -> None:
    for table in ("saved_jobs", "applications", "jobs", "sources"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_table("saved_jobs")
    op.drop_table("applications")

    op.drop_index("ix_jobs_posted_at", table_name="jobs")
    op.drop_index("ix_jobs_source", table_name="jobs")
    op.drop_index("ix_jobs_company", table_name="jobs")
    op.drop_constraint("fk_jobs_source_sources", "jobs", type_="foreignkey")
    op.drop_constraint("company_not_empty", "jobs", type_="check")
    op.drop_constraint("title_not_empty", "jobs", type_="check")
    op.execute("ALTER TABLE jobs RENAME CONSTRAINT uq_jobs_url TO jobs_url_key")
    op.alter_column(
        "jobs",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=True,
        server_default=None,
    )
    op.drop_column("jobs", "updated_at")

    op.drop_table("sources")
