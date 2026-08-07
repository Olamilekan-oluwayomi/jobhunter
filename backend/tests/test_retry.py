"""Tests for the retry helper."""

from __future__ import annotations

import pytest

from utils.retry import retry


def test_succeeds_first_time():
    calls = 0

    @retry(attempts=3)
    def work():
        nonlocal calls
        calls += 1
        return "ok"

    assert work() == "ok"
    assert calls == 1


def test_retries_then_succeeds():
    calls = 0

    @retry(attempts=3, delay=0.01)
    def work():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("boom")
        return "ok"

    assert work() == "ok"
    assert calls == 3


def test_exhausts_attempts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = 0

    @retry(attempts=3, delay=0.01, exceptions=(ValueError,))
    def work():
        nonlocal calls
        calls += 1
        raise ValueError("always")

    with pytest.raises(ValueError):
        work()
    assert calls == 3


def test_untargeted_exception_propagates_immediately(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = 0

    @retry(attempts=5, exceptions=(ConnectionError,))
    def work():
        nonlocal calls
        calls += 1
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        work()
    assert calls == 1
