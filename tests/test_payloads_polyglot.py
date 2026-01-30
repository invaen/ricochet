"""Tests for polyglot payload generator."""

import pytest

from ricochet.payloads.polyglot import PolyglotPayloadGenerator


class TestPolyglotPayloadGenerator:
    """Tests for PolyglotPayloadGenerator class."""

    def test_generator_yields_three_payloads(self):
        """Generator should yield exactly 3 polyglot payloads."""
        gen = PolyglotPayloadGenerator()
        payloads = list(gen.generate("http://callback.example.com"))
        assert len(payloads) == 3

    def test_vuln_type_returns_polyglot(self):
        """vuln_type property should return 'polyglot'."""
        gen = PolyglotPayloadGenerator()
        assert gen.vuln_type == "polyglot"

    def test_context_is_universal(self):
        """All payloads should have 'universal' context."""
        gen = PolyglotPayloadGenerator()
        for _, context in gen.generate("http://callback.example.com"):
            assert context == "universal", f"Expected 'universal' context, got '{context}'"

    def test_payload_tuple_format(self):
        """Each payload should be a tuple of (str, str)."""
        gen = PolyglotPayloadGenerator()
        for item in gen.generate("http://callback.example.com"):
            assert isinstance(item, tuple), f"Expected tuple, got {type(item)}"
            assert len(item) == 2, f"Expected 2-tuple, got {len(item)}-tuple"
            payload, context = item
            assert isinstance(payload, str), f"Payload should be str, got {type(payload)}"
            assert isinstance(context, str), f"Context should be str, got {type(context)}"

    def test_xss_polyglot_contains_callback(self):
        """XSS polyglot should contain {{CALLBACK}} placeholder."""
        gen = PolyglotPayloadGenerator()
        payloads = [p for p, _ in gen.generate("http://callback.example.com")]

        # At least one payload should have callback placeholder
        callback_payloads = [p for p in payloads if "{{CALLBACK}}" in p]
        assert len(callback_payloads) >= 1, "Expected at least one payload with {{CALLBACK}}"

    def test_ssti_polyglot_contains_template_syntax(self):
        """SSTI polyglot should contain template syntax markers."""
        gen = PolyglotPayloadGenerator()
        payloads = [p for p, _ in gen.generate("http://callback.example.com")]

        # Should find template engine syntax patterns
        ssti_indicators = ["{{", "<%", "${", "#{"]
        found_indicators = []

        for payload in payloads:
            for indicator in ssti_indicators:
                if indicator in payload:
                    found_indicators.append(indicator)

        assert len(found_indicators) >= 2, f"Expected SSTI indicators, found: {found_indicators}"

    def test_sqli_polyglot_contains_sleep(self):
        """SQLi polyglot should contain SLEEP for time-based detection."""
        gen = PolyglotPayloadGenerator()
        payloads = [p for p, _ in gen.generate("http://callback.example.com")]

        # At least one payload should have SLEEP
        sleep_payloads = [p for p in payloads if "SLEEP" in p]
        assert len(sleep_payloads) >= 1, "Expected at least one payload with SLEEP"

    def test_xss_polyglot_works_across_contexts(self):
        """XSS polyglot should escape multiple HTML contexts."""
        gen = PolyglotPayloadGenerator()
        payloads = [p for p, _ in gen.generate("http://callback.example.com")]

        # Find the XSS polyglot (contains onerror)
        xss_payloads = [p for p in payloads if "onerror" in p]
        assert len(xss_payloads) >= 1, "Expected XSS polyglot with onerror"

        xss_poly = xss_payloads[0]
        # Should break out of multiple contexts
        assert "'" in xss_poly or '"' in xss_poly, "Should escape attribute quotes"
        assert ">" in xss_poly, "Should close HTML tags"
