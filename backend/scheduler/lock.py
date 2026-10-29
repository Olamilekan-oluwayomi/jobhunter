"""Prevent overlapping CLI, API and scheduled scrapes across PostgreSQL workers."""

from contextlib import contextmanager

from sqlalchemy import text

from database.connection import engine


class ScrapeBusyError(RuntimeError):
    pass


@contextmanager
def scrape_lock():
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(728491632)"))
        if not acquired:
            raise ScrapeBusyError("A scrape is already running. Try again later.")
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(728491632)"))
