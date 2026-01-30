"""
Token bucket rate limiter for controlled request timing.

Prevents target bans by limiting request rate while supporting burst
allowances for initial request batches.
"""

import threading
import time
from typing import Optional


class RateLimiter:
    """
    Thread-safe token bucket rate limiter.

    Controls request rate to avoid overwhelming targets or triggering
    rate limit protections. Uses time.monotonic() for timing to avoid
    issues with system clock adjustments.

    Args:
        rate: Maximum requests per second (tokens added per second)
        burst: Maximum burst size (token bucket capacity). Default 1 means
               no bursting - each request must wait for its token.

    Example:
        >>> rl = RateLimiter(rate=10, burst=1)  # 10 req/s, no burst
        >>> for _ in range(5):
        ...     rl.acquire()  # Blocks until token available
        ...     send_request()
    """

    def __init__(self, rate: float, burst: int = 1) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        if burst < 1:
            raise ValueError("burst must be at least 1")

        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)  # Start with full bucket
        self._last_update = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time. Must hold lock."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_update = now

    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire a token to proceed with a request.

        Args:
            blocking: If True, wait until token available. If False, return
                     immediately with False if no token available.

        Returns:
            True if token acquired, False if non-blocking and no token.
        """
        while True:
            with self._lock:
                self._refill()

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

                if not blocking:
                    return False

                # Calculate wait time for next token
                wait_time = (1.0 - self._tokens) / self._rate

            # Release lock while sleeping to allow other threads
            time.sleep(wait_time)

    @property
    def rate(self) -> float:
        """Current rate limit in requests per second."""
        return self._rate

    @property
    def burst(self) -> int:
        """Maximum burst size (bucket capacity)."""
        return self._burst

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (approximate)."""
        with self._lock:
            self._refill()
            return self._tokens
