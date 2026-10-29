"""UTC timestamps compatible with the existing timezone-naive database schema."""

from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
