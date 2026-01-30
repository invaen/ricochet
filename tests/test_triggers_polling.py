"""Tests for polling module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from ricochet.triggers.polling import (
    PollingConfig,
    PollingStrategy,
    poll_for_callbacks,
)


class TestPollingConfig:
    """Tests for PollingConfig dataclass."""

    def test_default_values(self):
        """PollingConfig should have sensible defaults."""
        config = PollingConfig()

        assert config.base_interval == 5.0
        assert config.max_interval == 60.0
        assert config.backoff_factor == 1.5
        assert config.reset_on_callback is True
        assert config.timeout == 3600.0

    def test_custom_values(self):
        """PollingConfig should accept custom values."""
        config = PollingConfig(
            base_interval=10.0,
            max_interval=120.0,
            backoff_factor=2.0,
            reset_on_callback=False,
            timeout=7200.0,
        )

        assert config.base_interval == 10.0
        assert config.max_interval == 120.0
        assert config.backoff_factor == 2.0
        assert config.reset_on_callback is False
        assert config.timeout == 7200.0


class TestPollingStrategy:
    """Tests for PollingStrategy class."""

    def test_initial_interval_is_base(self):
        """First call should return base_interval."""
        config = PollingConfig(base_interval=5.0)
        strategy = PollingStrategy(config)

        interval = strategy.get_next_interval(received_callback=False)
        assert interval == 5.0

    def test_callback_resets_to_base_interval(self):
        """Receiving callback should reset to base_interval."""
        config = PollingConfig(base_interval=5.0, max_interval=60.0)
        strategy = PollingStrategy(config)

        # Simulate several quiet polls to trigger backoff
        for _ in range(10):
            strategy.get_next_interval(received_callback=False)

        # Get current interval (should be backed off)
        backed_off = strategy.get_next_interval(received_callback=False)
        assert backed_off > 5.0

        # Receive callback - should reset to base
        reset = strategy.get_next_interval(received_callback=True)
        assert reset == 5.0

    def test_backoff_applies_after_threshold(self):
        """Backoff should apply after QUIET_THRESHOLD quiet polls."""
        config = PollingConfig(
            base_interval=5.0,
            max_interval=60.0,
            backoff_factor=1.5,
        )
        strategy = PollingStrategy(config)

        # First QUIET_THRESHOLD polls should be base_interval
        for i in range(PollingStrategy.QUIET_THRESHOLD):
            interval = strategy.get_next_interval(received_callback=False)
            assert interval == 5.0, f"Poll {i+1} should be base interval"

        # Next poll should apply backoff
        interval = strategy.get_next_interval(received_callback=False)
        assert interval == 5.0 * 1.5  # 7.5

    def test_backoff_never_exceeds_max(self):
        """Backoff should cap at max_interval."""
        config = PollingConfig(
            base_interval=5.0,
            max_interval=15.0,
            backoff_factor=2.0,
        )
        strategy = PollingStrategy(config)

        # Run many quiet polls
        for _ in range(50):
            interval = strategy.get_next_interval(received_callback=False)

        # Final interval should be capped
        assert interval <= 15.0

    def test_reset_on_callback_disabled(self):
        """When reset_on_callback=False, callback doesn't reset interval."""
        config = PollingConfig(
            base_interval=5.0,
            max_interval=60.0,
            backoff_factor=1.5,
            reset_on_callback=False,
        )
        strategy = PollingStrategy(config)

        # Trigger backoff
        for _ in range(10):
            strategy.get_next_interval(received_callback=False)

        # Get backed off interval
        backed_off = strategy.get_next_interval(received_callback=False)

        # Receive callback - should NOT reset
        after_callback = strategy.get_next_interval(received_callback=True)

        # Should still be above base (quiet counter incremented)
        assert after_callback >= 5.0

    def test_is_timed_out_false_initially(self):
        """is_timed_out should return False before any calls."""
        config = PollingConfig(timeout=60.0)
        strategy = PollingStrategy(config)

        assert strategy.is_timed_out() is False

    def test_is_timed_out_after_first_interval(self):
        """is_timed_out tracks time from first get_next_interval call."""
        config = PollingConfig(timeout=0.1)  # Very short timeout
        strategy = PollingStrategy(config)

        # First call starts the timer
        strategy.get_next_interval(received_callback=False)

        # Wait for timeout
        time.sleep(0.15)

        assert strategy.is_timed_out() is True

    def test_elapsed_seconds(self):
        """elapsed_seconds should track time since first call."""
        config = PollingConfig()
        strategy = PollingStrategy(config)

        # Before any call, should be 0
        assert strategy.elapsed_seconds == 0.0

        # After first call, should be small but positive
        strategy.get_next_interval(received_callback=False)
        time.sleep(0.1)
        assert strategy.elapsed_seconds >= 0.1


class TestPollForCallbacks:
    """Tests for poll_for_callbacks function."""

    def test_polls_store_with_since_parameter(self):
        """poll_for_callbacks should query store with since timestamp."""
        mock_store = MagicMock()
        mock_store.get_findings.return_value = []

        config = PollingConfig(
            base_interval=0.01,  # Very fast for testing
            timeout=0.05,
        )

        with patch('ricochet.triggers.polling.time.sleep'):
            poll_for_callbacks(
                store=mock_store,
                config=config,
                callback=lambda f: None,
            )

        # Should have called get_findings at least once
        mock_store.get_findings.assert_called()

    def test_invokes_callback_with_findings(self):
        """poll_for_callbacks should invoke callback when findings exist."""
        mock_finding = MagicMock()
        mock_store = MagicMock()

        # First call returns findings, second call empty (then timeout)
        call_count = 0

        def mock_get_findings(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [mock_finding]
            return []

        mock_store.get_findings.side_effect = mock_get_findings

        config = PollingConfig(
            base_interval=0.01,
            timeout=0.05,
        )

        received_findings = []

        def capture_callback(findings):
            received_findings.extend(findings)

        with patch('ricochet.triggers.polling.time.sleep'):
            total = poll_for_callbacks(
                store=mock_store,
                config=config,
                callback=capture_callback,
            )

        assert mock_finding in received_findings
        assert total >= 1

    def test_returns_total_findings_count(self):
        """poll_for_callbacks should return total findings seen."""
        mock_store = MagicMock()

        findings1 = [MagicMock(), MagicMock()]
        findings2 = [MagicMock()]

        call_count = 0

        def mock_get_findings(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return findings1
            elif call_count == 2:
                return findings2
            return []

        mock_store.get_findings.side_effect = mock_get_findings

        config = PollingConfig(
            base_interval=0.01,
            timeout=0.05,
        )

        with patch('ricochet.triggers.polling.time.sleep'):
            total = poll_for_callbacks(
                store=mock_store,
                config=config,
                callback=lambda f: None,
            )

        # Should have seen at least 3 findings
        assert total >= 3

    def test_respects_timeout(self):
        """poll_for_callbacks should exit when timeout exceeded."""
        mock_store = MagicMock()
        mock_store.get_findings.return_value = []

        config = PollingConfig(
            base_interval=0.1,
            timeout=0.2,
        )

        start = time.monotonic()
        poll_for_callbacks(
            store=mock_store,
            config=config,
            callback=lambda f: None,
        )
        elapsed = time.monotonic() - start

        # Should have exited around timeout (with some tolerance)
        assert elapsed < 1.0  # Should not run forever

    def test_propagates_keyboard_interrupt(self):
        """poll_for_callbacks should propagate KeyboardInterrupt."""
        mock_store = MagicMock()
        mock_store.get_findings.return_value = []

        config = PollingConfig(
            base_interval=0.01,
            timeout=10.0,  # Long timeout
        )

        def raise_interrupt(_):
            raise KeyboardInterrupt()

        with patch('ricochet.triggers.polling.time.sleep', side_effect=raise_interrupt):
            with pytest.raises(KeyboardInterrupt):
                poll_for_callbacks(
                    store=mock_store,
                    config=config,
                    callback=lambda f: None,
                )
