"""Polling infrastructure for callback monitoring."""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ricochet.core.store import InjectionStore
from ricochet.output.finding import Finding


@dataclass
class PollingConfig:
    """Configuration for polling behavior.

    Attributes:
        base_interval: Starting interval between polls (seconds).
        max_interval: Maximum interval after backoff (seconds).
        backoff_factor: Multiplier for interval on quiet periods.
        reset_on_callback: Reset to base interval when callback received.
        timeout: Maximum total polling duration (seconds).
    """
    base_interval: float = 5.0
    max_interval: float = 60.0
    backoff_factor: float = 1.5
    reset_on_callback: bool = True
    timeout: float = 3600.0  # 1 hour default


class PollingStrategy:
    """Adaptive polling with exponential backoff.

    Implements an intelligent polling schedule that:
    - Starts at base_interval (default 5s)
    - Backs off after 5 consecutive quiet polls
    - Resets to base interval on callback receipt
    - Never exceeds max_interval

    Example:
        >>> config = PollingConfig(base_interval=5.0, max_interval=60.0)
        >>> strategy = PollingStrategy(config)
        >>> interval = strategy.get_next_interval(received_callback=False)
        5.0
        >>> # After 5 quiet polls, starts backing off
        >>> for _ in range(5):
        ...     interval = strategy.get_next_interval(False)
        >>> interval  # Now > 5.0
        7.5
    """

    # Number of quiet polls before backoff kicks in
    QUIET_THRESHOLD = 5

    def __init__(self, config: PollingConfig):
        """Initialize polling strategy.

        Args:
            config: PollingConfig with timing parameters.
        """
        self._config = config
        self._current_interval = config.base_interval
        self._quiet_polls = 0
        self._start_time: Optional[float] = None

    def get_next_interval(self, received_callback: bool) -> float:
        """Get the next polling interval.

        Args:
            received_callback: True if callback was received since last poll.

        Returns:
            Next interval in seconds.
        """
        # Initialize start time on first call
        if self._start_time is None:
            self._start_time = time.monotonic()

        if received_callback and self._config.reset_on_callback:
            # Reset to base interval on callback
            self._current_interval = self._config.base_interval
            self._quiet_polls = 0
        else:
            # Increment quiet poll counter
            self._quiet_polls += 1

            # Apply backoff after threshold
            if self._quiet_polls > self.QUIET_THRESHOLD:
                self._current_interval = min(
                    self._current_interval * self._config.backoff_factor,
                    self._config.max_interval
                )

        return self._current_interval

    def is_timed_out(self) -> bool:
        """Check if polling has exceeded timeout.

        Returns:
            True if elapsed time exceeds configured timeout.
        """
        if self._start_time is None:
            return False

        elapsed = time.monotonic() - self._start_time
        return elapsed > self._config.timeout

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since polling started.

        Returns:
            Elapsed time in seconds, or 0 if not started.
        """
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time


def poll_for_callbacks(
    store: InjectionStore,
    config: PollingConfig,
    callback: Callable[[list[Finding]], None],
    min_severity: str = 'info'
) -> int:
    """Poll for new callbacks with adaptive intervals.

    Continuously polls the store for new findings, calling the user
    callback function with any new findings. Uses exponential backoff
    during quiet periods to reduce load.

    Args:
        store: InjectionStore to query for findings.
        config: PollingConfig with timing parameters.
        callback: Function to call with new findings list.
        min_severity: Minimum severity level to report.

    Returns:
        Total count of findings seen during polling.

    Raises:
        KeyboardInterrupt: Propagated when user interrupts.
    """
    strategy = PollingStrategy(config)
    total_findings = 0
    last_poll_time: Optional[float] = None

    try:
        while not strategy.is_timed_out():
            # Query for new findings
            findings = store.get_findings(
                since=last_poll_time,
                min_severity=min_severity
            )

            # Update last poll time for next iteration
            last_poll_time = time.time()

            # Call user callback if findings found
            received_callback = len(findings) > 0
            if received_callback:
                total_findings += len(findings)
                callback(findings)

            # Get next interval and sleep
            interval = strategy.get_next_interval(received_callback)
            time.sleep(interval)

    except KeyboardInterrupt:
        # Propagate interrupt for clean exit
        raise

    return total_findings
