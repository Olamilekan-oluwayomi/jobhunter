"""Standardise application statuses to saved/applied/interview/rejected/offer.

Replaces the legacy 'interviewing' status with 'interview'. The change is
safe: no existing rows use 'interviewing' (verified before shipping), and the
constraint is swapped in place without touching the table's data.
"""

from alembic import op

revision = "0005_application_statuses"
down_revision = "0004_job_scores"
branch_labels = None
depends_on = None

_CONSTRAINT = "ck_applications_valid_status"
_NEW_STATUSES = "('applied', 'interview', 'offer', 'rejected')"
_OLD_STATUSES = "('applied', 'interviewing', 'offer', 'rejected')"


def upgrade() -> None:
    op.execute(f"ALTER TABLE applications DROP CONSTRAINT {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE applications ADD CONSTRAINT {_CONSTRAINT} CHECK (status IN {_NEW_STATUSES})"
    )


def downgrade() -> None:
    op.execute(f"ALTER TABLE applications DROP CONSTRAINT {_CONSTRAINT}")
    op.execute(
        f"ALTER TABLE applications ADD CONSTRAINT {_CONSTRAINT} CHECK (status IN {_OLD_STATUSES})"
    )
