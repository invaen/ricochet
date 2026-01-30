"""Tests for XSS metadata capture and display."""

import json
from io import StringIO

import pytest

from ricochet.output.finding import Finding
from ricochet.output.formatters import output_json, output_text
from ricochet.payloads.xss import XSSPayloadGenerator


def make_finding(callback_body: bytes | None = None, context: str = "xss") -> Finding:
    """Create a Finding with specified callback body."""
    return Finding(
        correlation_id="test123",
        target_url="http://target.com/form",
        parameter="comment",
        payload="<script>test</script>",
        context=context,
        injected_at=1000.0,
        callback_id=1,
        source_ip="10.0.0.1",
        request_path="/test123",
        callback_headers={"User-Agent": "Mozilla/5.0"},
        callback_body=callback_body,
        received_at=1005.0,
        delay_seconds=5.0,
    )


class TestFindingMetadata:
    """Tests for Finding.metadata property."""

    def test_metadata_with_valid_json(self):
        """Finding.metadata returns dict when callback body is valid JSON."""
        body = json.dumps({
            "url": "http://victim.com/admin",
            "cookies": "session=abc123",
            "dom": "<html>...</html>",
            "ua": "Mozilla/5.0"
        }).encode()
        finding = make_finding(callback_body=body)

        assert finding.has_metadata is True
        assert finding.metadata is not None
        assert finding.metadata["url"] == "http://victim.com/admin"
        assert finding.metadata["cookies"] == "session=abc123"
        assert finding.metadata["ua"] == "Mozilla/5.0"

    def test_metadata_with_none_body(self):
        """Finding.metadata returns None when callback body is None."""
        finding = make_finding(callback_body=None)

        assert finding.has_metadata is False
        assert finding.metadata is None

    def test_metadata_with_empty_body(self):
        """Finding.metadata returns None when callback body is empty."""
        finding = make_finding(callback_body=b"")

        assert finding.has_metadata is False
        assert finding.metadata is None

    def test_metadata_with_invalid_json(self):
        """Finding.metadata returns None when body is not valid JSON."""
        finding = make_finding(callback_body=b"not json data")

        assert finding.has_metadata is False
        assert finding.metadata is None

    def test_metadata_with_json_array(self):
        """Finding.metadata returns None when body is JSON array (not dict)."""
        finding = make_finding(callback_body=b'["a", "b", "c"]')

        assert finding.has_metadata is False
        assert finding.metadata is None

    def test_metadata_with_json_string(self):
        """Finding.metadata returns None when body is JSON string (not dict)."""
        finding = make_finding(callback_body=b'"just a string"')

        assert finding.has_metadata is False
        assert finding.metadata is None


class TestOutputJsonMetadata:
    """Tests for metadata in JSON output."""

    def test_json_includes_metadata(self):
        """output_json includes metadata object when present."""
        body = json.dumps({
            "url": "http://victim.com",
            "cookies": "token=xyz"
        }).encode()
        finding = make_finding(callback_body=body)

        output = StringIO()
        output_json([finding], file=output)
        result = json.loads(output.getvalue())

        assert "metadata" in result["finding"]["callback"]
        assert result["finding"]["callback"]["metadata"]["url"] == "http://victim.com"
        assert result["finding"]["callback"]["metadata"]["cookies"] == "token=xyz"

    def test_json_no_metadata_without_json_body(self):
        """output_json omits metadata key when body is not JSON."""
        finding = make_finding(callback_body=b"plain text")

        output = StringIO()
        output_json([finding], file=output)
        result = json.loads(output.getvalue())

        assert "metadata" not in result["finding"]["callback"]


class TestOutputTextMetadata:
    """Tests for metadata in text output."""

    def test_text_shows_metadata_in_verbose(self):
        """output_text shows captured metadata in verbose mode."""
        body = json.dumps({
            "url": "http://victim.com/admin",
            "cookies": "session=abc123; admin=true",
            "ua": "Mozilla/5.0 (Windows NT 10.0)",
            "dom": "<html><body><h1>Admin Panel</h1></body></html>"
        }).encode()
        finding = make_finding(callback_body=body)

        output = StringIO()
        output_text([finding], file=output, verbose=True)
        text = output.getvalue()

        assert "=== Captured Metadata ===" in text
        assert "Victim URL: http://victim.com/admin" in text
        assert "Cookies: session=abc123; admin=true" in text
        assert "User-Agent: Mozilla/5.0 (Windows NT 10.0)" in text
        assert "DOM: <html><body><h1>Admin Panel</h1></body></html>..." in text

    def test_text_no_metadata_without_verbose(self):
        """output_text does not show metadata without verbose flag."""
        body = json.dumps({"url": "http://victim.com"}).encode()
        finding = make_finding(callback_body=body)

        output = StringIO()
        output_text([finding], file=output, verbose=False)
        text = output.getvalue()

        assert "=== Captured Metadata ===" not in text
        assert "Victim URL:" not in text

    def test_text_truncates_long_cookies(self):
        """output_text truncates cookies longer than 100 chars."""
        long_cookies = "a" * 150
        body = json.dumps({"cookies": long_cookies}).encode()
        finding = make_finding(callback_body=body)

        output = StringIO()
        output_text([finding], file=output, verbose=True)
        text = output.getvalue()

        assert "Cookies: " + "a" * 100 + "..." in text


class TestXSSPayloadGenerator:
    """Tests for XSS exfiltration payload generator."""

    def test_generate_exfil_yields_payloads(self):
        """generate_exfil yields payloads from xss-exfil.txt."""
        gen = XSSPayloadGenerator()
        payloads = list(gen.generate_exfil("http://callback.test"))

        assert len(payloads) >= 5  # At least 5 exfil payloads

    def test_generate_exfil_context_is_html_exfil(self):
        """generate_exfil yields context 'html:exfil'."""
        gen = XSSPayloadGenerator()
        payloads = list(gen.generate_exfil("http://callback.test"))

        for payload, context in payloads:
            assert context == "html:exfil"

    def test_generate_exfil_payloads_have_callback_placeholder(self):
        """All exfil payloads contain {{CALLBACK}} placeholder."""
        gen = XSSPayloadGenerator()
        payloads = list(gen.generate_exfil("http://callback.test"))

        for payload, context in payloads:
            assert "{{CALLBACK}}" in payload

    def test_generate_exfil_payloads_capture_metadata(self):
        """Exfil payloads contain code to capture cookies, URL, DOM."""
        gen = XSSPayloadGenerator()
        payloads = list(gen.generate_exfil("http://callback.test"))

        # At least some payloads should capture these
        all_payload_text = " ".join(p for p, _ in payloads)
        assert "cookie" in all_payload_text.lower()
        assert "location" in all_payload_text.lower()
