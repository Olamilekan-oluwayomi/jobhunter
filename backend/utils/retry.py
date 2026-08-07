"""Small, dependency-free retry decorator for transient failures."""

from __future__ import annotations

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger("utils.retry")

T = TypeVar("T")


def retry(
    *,
    attempts: int = 3,
    delay: float = 0.5,
    backoff: float = 2.0,
    jitter: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a callable with exponential backoff and optional jitter.

    Attempts are capped at ``attempts``; any exception in ``exceptions``
    triggers a retry after ``delay`` seconds, multiplied by ``backoff`` per
    retry. All other exceptions propagate immediately.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 1
            current_delay = delay
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt >= attempts:
                        logger.warning(
                            "retry exhausted for %s after %s attempt(s): %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        raise
                    wait = current_delay
                    if jitter:
                        wait += random.uniform(0, jitter)
                    logger.info(
                        "retrying %s in %.2fs (attempt %d/%d): %s",
                        func.__name__,
                        wait,
                        attempt,
                        attempts,
                        exc,
                    )
                    time.sleep(wait)
                    current_delay *= backoff
                    attempt += 1

        return wrapper

    return decorator
