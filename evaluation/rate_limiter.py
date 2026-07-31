"""
Rate limiter for Gemini API calls.

Implements a simple interval-based rate limiter (12 RPM target)
with exponential backoff on 429 errors to stay safely under the
15 RPM free-tier limit of gemini-3.1-flash-lite.
"""
import time
import logging
from typing import Callable, TypeVar

from openai import RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Backoff delays in seconds for consecutive 429 errors
_BACKOFF_SCHEDULE = [10, 30, 60]


class RateLimiter:
    """
    Interval-based rate limiter targeting a configurable RPM.

    Usage:
        rl = RateLimiter(rpm=12)
        result = rl.call_with_retry(lambda: api_client.do_something())
    """

    def __init__(self, rpm: int = 12) -> None:
        """
        Args:
            rpm: Target requests per minute. Defaults to 12 (buffer under 15 RPM limit).
        """
        self._min_interval: float = 60.0 / rpm   # seconds between calls
        self._last_call_time: float = 0.0

    def wait(self) -> None:
        """Sleep if necessary to maintain the target RPM."""
        elapsed = time.monotonic() - self._last_call_time
        remaining = self._min_interval - elapsed
        if remaining > 0:
            logger.debug(f"[RateLimiter] Sleeping {remaining:.1f}s to respect rate limit.")
            time.sleep(remaining)
        self._last_call_time = time.monotonic()

    def call_with_retry(self, fn: Callable[[], T], max_retries: int = 3) -> T:
        """
        Execute fn() with rate limiting and exponential backoff on 429 errors.

        Backoff schedule: 10s → 30s → 60s on consecutive failures.

        Args:
            fn: A zero-argument callable that makes a single API call.
            max_retries: Maximum number of retries after a 429 error.

        Returns:
            The return value of fn().

        Raises:
            RateLimitError: If all retries are exhausted.
            Exception: Any non-rate-limit exception from fn().
        """
        for attempt in range(max_retries + 1):
            try:
                self.wait()
                return fn()
            except RateLimitError:
                if attempt == max_retries:
                    logger.error("[RateLimiter] Max retries exhausted. Raising.")
                    raise
                delay = _BACKOFF_SCHEDULE[min(attempt, len(_BACKOFF_SCHEDULE) - 1)]
                logger.warning(
                    f"[RateLimiter] 429 received (attempt {attempt + 1}/{max_retries}). "
                    f"Backing off for {delay}s..."
                )
                time.sleep(delay)
                # Reset last call time so next wait() doesn't double-count
                self._last_call_time = time.monotonic()

        raise RuntimeError("call_with_retry: unreachable code path")
