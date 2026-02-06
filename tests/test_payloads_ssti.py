"""Tests for SSTI payload generator."""

import pytest

from ricochet.payloads.ssti import SSTIPayloadGenerator


class TestSSTIPayloadGenerator:
    """Tests for SSTIPayloadGenerator class."""

    def test_generator_yields_non_empty_list(self):
        """Generator should yield at least one payload."""
        gen = SSTIPayloadGenerator()
        payloads = list(gen.generate("http://callback.example.com"))
        assert len(payloads) > 0

    def test_minimum_six_payloads(self):
        """Generator should yield at least 6 payloads (2 per engine)."""
        gen = SSTIPayloadGenerator()
        payloads = list(gen.generate("http://callback.example.com"))
        assert len(payloads) >= 6

    def test_all_payloads_contain_callback_placeholder(self):
        """All payloads should contain {{CALLBACK}} placeholder."""
        gen = SSTIPayloadGenerator()
        for payload, _ in gen.generate("http://callback.example.com"):
            assert "{{CALLBACK}}" in payload, f"Payload missing placeholder: {payload}"

    def test_vuln_type_returns_ssti(self):
        """vuln_type property should return 'ssti'."""
        gen = SSTIPayloadGenerator()
        assert gen.vuln_type == "ssti"

    def test_payload_tuple_format(self):
        """Each payload should be a tuple of (str, str)."""
        gen = SSTIPayloadGenerator()
        for item in gen.generate("http://callback.example.com"):
            assert isinstance(item, tuple), f"Expected tuple, got {type(item)}"
            assert len(item) == 2, f"Expected 2-tuple, got {len(item)}-tuple"
            payload, engine = item
            assert isinstance(payload, str), f"Payload should be str, got {type(payload)}"
            assert isinstance(engine, str), f"Engine should be str, got {type(engine)}"

    def test_generates_for_all_engines_by_default(self):
        """Without engine parameter, should generate for all engines."""
        gen = SSTIPayloadGenerator()
        payloads = list(gen.generate("http://callback.example.com"))
        engines = set(p[1] for p in payloads)

        # Should have payloads for all three engines
        assert "jinja2" in engines
        assert "freemarker" in engines
        assert "twig" in engines

    def test_engine_specific_jinja2(self):
        """With engine='jinja2', should only generate jinja2 payloads."""
        gen = SSTIPayloadGenerator(engine="jinja2")
        payloads = list(gen.generate("http://callback.example.com"))

        assert len(payloads) >= 2
        assert all(p[1] == "jinja2" for p in payloads)

    def test_engine_specific_freemarker(self):
        """With engine='freemarker', should only generate freemarker payloads."""
        gen = SSTIPayloadGenerator(engine="freemarker")
        payloads = list(gen.generate("http://callback.example.com"))

        assert len(payloads) >= 2
        assert all(p[1] == "freemarker" for p in payloads)

    def test_engine_specific_twig(self):
        """With engine='twig', should only generate twig payloads."""
        gen = SSTIPayloadGenerator(engine="twig")
        payloads = list(gen.generate("http://callback.example.com"))

        assert len(payloads) >= 2
        assert all(p[1] == "twig" for p in payloads)

    def test_invalid_engine_raises_error(self):
        """Specifying unknown engine should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            SSTIPayloadGenerator(engine="django")
        assert "Unknown engine" in str(exc_info.value)
        assert "django" in str(exc_info.value)

    def test_payloads_use_command_execution(self):
        """Payloads should use curl/nslookup for callbacks."""
        gen = SSTIPayloadGenerator()
        payloads = [p for p, _ in gen.generate("http://callback.example.com")]

        command_methods = ["curl", "nslookup", "wget"]
        found_methods = set()

        for payload in payloads:
            for method in command_methods:
                if method in payload:
                    found_methods.add(method)

        # Should find at least 2 different command methods
        assert len(found_methods) >= 2, f"Expected at least 2 command methods, found: {found_methods}"

    def test_engines_list_class_attribute(self):
        """ENGINES class attribute should list supported engines."""
        assert SSTIPayloadGenerator.ENGINES == ["jinja2", "freemarker", "twig", "erb", "velocity", "mako"]
