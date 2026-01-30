"""Tests for active trigger probing module."""

import pytest
from unittest.mock import Mock, patch

from ricochet.triggers.active import (
    ActiveTrigger,
    TRIGGER_ENDPOINTS,
    TriggerResult,
)


class TestTriggerEndpoints:
    """Tests for TRIGGER_ENDPOINTS list."""

    def test_contains_expected_paths(self):
        """Should contain expected admin/support/analytics paths."""
        expected = ["/admin", "/support", "/analytics", "/dashboard"]
        for path in expected:
            assert path in TRIGGER_ENDPOINTS, f"Missing expected endpoint: {path}"

    def test_all_paths_start_with_slash(self):
        """All endpoints should start with /."""
        for endpoint in TRIGGER_ENDPOINTS:
            assert endpoint.startswith("/"), f"Endpoint missing leading slash: {endpoint}"

    def test_minimum_endpoint_count(self):
        """Should have at least 20 endpoints."""
        assert len(TRIGGER_ENDPOINTS) >= 20, f"Expected 20+ endpoints, got {len(TRIGGER_ENDPOINTS)}"


class TestTriggerResult:
    """Tests for TriggerResult dataclass."""

    def test_fields_accessible(self):
        """All fields should be accessible."""
        result = TriggerResult(
            endpoint="/admin",
            status=200,
            error=None,
            response_size=1024,
        )
        assert result.endpoint == "/admin"
        assert result.status == 200
        assert result.error is None
        assert result.response_size == 1024

    def test_error_result(self):
        """Should handle error results correctly."""
        result = TriggerResult(
            endpoint="/timeout-test",
            status=None,
            error="timeout",
            response_size=0,
        )
        assert result.status is None
        assert result.error == "timeout"
        assert result.response_size == 0


class TestActiveTrigger:
    """Tests for ActiveTrigger class."""

    def test_init_normalizes_url(self):
        """Should normalize base URL by removing trailing slash."""
        trigger = ActiveTrigger("https://example.com/")
        assert trigger.base_url == "https://example.com"

    def test_init_preserves_url_without_slash(self):
        """Should preserve URL without trailing slash."""
        trigger = ActiveTrigger("https://example.com")
        assert trigger.base_url == "https://example.com"

    @patch("ricochet.triggers.active.send_request")
    def test_probe_endpoint_success(self, mock_send):
        """Should return TriggerResult with status on success."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b"<html>Admin Panel</html>"
        mock_send.return_value = mock_response

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        result = trigger.probe_endpoint("/admin")

        assert result.endpoint == "/admin"
        assert result.status == 200
        assert result.error is None
        assert result.response_size == len(mock_response.body)

    @patch("ricochet.triggers.active.send_request")
    def test_probe_endpoint_timeout(self, mock_send):
        """Should return TriggerResult with error on timeout."""
        mock_send.side_effect = TimeoutError("Request timed out")

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        result = trigger.probe_endpoint("/slow")

        assert result.endpoint == "/slow"
        assert result.status is None
        assert result.error == "timeout"
        assert result.response_size == 0

    @patch("ricochet.triggers.active.send_request")
    def test_probe_endpoint_connection_error(self, mock_send):
        """Should return TriggerResult with error on connection failure."""
        mock_send.side_effect = ConnectionError("Connection refused")

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        result = trigger.probe_endpoint("/error")

        assert result.endpoint == "/error"
        assert result.status is None
        assert "Connection refused" in result.error
        assert result.response_size == 0

    @patch("ricochet.triggers.active.send_request")
    def test_probe_endpoint_constructs_correct_url(self, mock_send):
        """Should construct correct URL from base_url + endpoint."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b""
        mock_send.return_value = mock_response

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        trigger.probe_endpoint("/admin/users")

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.kwargs["url"] == "https://example.com/admin/users"

    @patch("ricochet.triggers.active.send_request")
    def test_probe_endpoint_adds_slash_if_missing(self, mock_send):
        """Should add leading slash if endpoint missing it."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b""
        mock_send.return_value = mock_response

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        result = trigger.probe_endpoint("admin")  # No leading slash

        assert result.endpoint == "/admin"

    @patch("ricochet.triggers.active.send_request")
    def test_probe_all_uses_default_endpoints(self, mock_send):
        """Should use TRIGGER_ENDPOINTS when none provided."""
        mock_response = Mock()
        mock_response.status = 404
        mock_response.body = b""
        mock_send.return_value = mock_response

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        results = trigger.probe_all()

        assert len(results) == len(TRIGGER_ENDPOINTS)

    @patch("ricochet.triggers.active.send_request")
    def test_probe_all_uses_custom_endpoints(self, mock_send):
        """Should use custom endpoints when provided."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b""
        mock_send.return_value = mock_response

        custom_endpoints = ["/custom1", "/custom2", "/custom3"]
        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        results = trigger.probe_all(endpoints=custom_endpoints)

        assert len(results) == 3
        assert results[0].endpoint == "/custom1"
        assert results[1].endpoint == "/custom2"
        assert results[2].endpoint == "/custom3"

    @patch("ricochet.triggers.active.send_request")
    def test_probe_all_calls_callback(self, mock_send):
        """Should call callback for each result."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b""
        mock_send.return_value = mock_response

        callback = Mock()
        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        results = trigger.probe_all(endpoints=["/a", "/b"], callback=callback)

        assert callback.call_count == 2
        # Verify callback was called with TriggerResult instances
        for call in callback.call_args_list:
            assert isinstance(call.args[0], TriggerResult)

    @patch("ricochet.triggers.active.send_request")
    def test_probe_all_returns_all_results(self, mock_send):
        """Should return results for all endpoints."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b"content"
        mock_send.return_value = mock_response

        trigger = ActiveTrigger("https://example.com", rate_limit=100.0)
        endpoints = ["/one", "/two", "/three"]
        results = trigger.probe_all(endpoints=endpoints)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.endpoint == endpoints[i]
            assert result.status == 200

    @patch("ricochet.triggers.active.send_request")
    def test_probe_passes_proxy_url(self, mock_send):
        """Should pass proxy_url to send_request."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b""
        mock_send.return_value = mock_response

        trigger = ActiveTrigger(
            "https://example.com",
            rate_limit=100.0,
            proxy_url="http://127.0.0.1:8080"
        )
        trigger.probe_endpoint("/admin")

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.kwargs["proxy_url"] == "http://127.0.0.1:8080"

    @patch("ricochet.triggers.active.send_request")
    def test_probe_passes_timeout(self, mock_send):
        """Should pass timeout to send_request."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.body = b""
        mock_send.return_value = mock_response

        trigger = ActiveTrigger(
            "https://example.com",
            rate_limit=100.0,
            timeout=30.0
        )
        trigger.probe_endpoint("/admin")

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.kwargs["timeout"] == 30.0
