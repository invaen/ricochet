"""Tests for XSS payload generator."""

import pytest

from ricochet.payloads.xss import XSSPayloadGenerator


class TestXSSPayloadGenerator:
    """Tests for XSSPayloadGenerator class."""

    def test_generator_yields_non_empty_list(self):
        """Generator should yield at least one payload."""
        gen = XSSPayloadGenerator()
        payloads = list(gen.generate("http://callback.example.com"))
        assert len(payloads) > 0

    def test_minimum_five_payloads(self):
        """Generator should yield at least 5 payloads."""
        gen = XSSPayloadGenerator()
        payloads = list(gen.generate("http://callback.example.com"))
        assert len(payloads) >= 5

    def test_all_payloads_contain_callback_placeholder(self):
        """All payloads should contain {{CALLBACK}} placeholder."""
        gen = XSSPayloadGenerator()
        for payload, _ in gen.generate("http://callback.example.com"):
            assert "{{CALLBACK}}" in payload, f"Payload missing placeholder: {payload}"

    def test_vuln_type_returns_xss(self):
        """vuln_type property should return 'xss'."""
        gen = XSSPayloadGenerator()
        assert gen.vuln_type == "xss"

    def test_payload_tuple_format(self):
        """Each payload should be a tuple of (str, str)."""
        gen = XSSPayloadGenerator()
        for item in gen.generate("http://callback.example.com"):
            assert isinstance(item, tuple), f"Expected tuple, got {type(item)}"
            assert len(item) == 2, f"Expected 2-tuple, got {len(item)}-tuple"
            payload, context = item
            assert isinstance(payload, str), f"Payload should be str, got {type(payload)}"
            assert isinstance(context, str), f"Context should be str, got {type(context)}"

    def test_payloads_use_browser_native_methods(self):
        """Payloads should use browser-native callback methods."""
        gen = XSSPayloadGenerator()
        payloads = [p for p, _ in gen.generate("http://callback.example.com")]

        # Check that payloads use various browser-native methods
        browser_methods = ["fetch", "src=", "onerror", "onload", "onfocus"]
        found_methods = set()

        for payload in payloads:
            for method in browser_methods:
                if method in payload:
                    found_methods.add(method)

        # Should find at least 3 different browser methods
        assert len(found_methods) >= 3, f"Expected at least 3 browser methods, found: {found_methods}"

    def test_context_is_html(self):
        """All payloads should have 'html' context."""
        gen = XSSPayloadGenerator()
        for _, context in gen.generate("http://callback.example.com"):
            assert context == "html", f"Expected 'html' context, got '{context}'"
