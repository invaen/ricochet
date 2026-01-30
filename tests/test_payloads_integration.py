"""Integration tests for all payload generators."""

import pytest

from ricochet.payloads import (
    XSSPayloadGenerator,
    SQLiPayloadGenerator,
    SSTIPayloadGenerator,
    PolyglotPayloadGenerator,
)


class TestPayloadModuleExports:
    """Test that all generators are properly exported from module."""

    def test_all_generators_importable(self):
        """All 4 generators should be importable from ricochet.payloads."""
        # Import should not raise
        from ricochet.payloads import XSSPayloadGenerator
        from ricochet.payloads import SQLiPayloadGenerator
        from ricochet.payloads import SSTIPayloadGenerator
        from ricochet.payloads import PolyglotPayloadGenerator

        assert XSSPayloadGenerator is not None
        assert SQLiPayloadGenerator is not None
        assert SSTIPayloadGenerator is not None
        assert PolyglotPayloadGenerator is not None

    def test_module_all_contains_all_exports(self):
        """__all__ should list all 4 generators."""
        from ricochet import payloads

        expected = {
            "XSSPayloadGenerator",
            "SQLiPayloadGenerator",
            "SSTIPayloadGenerator",
            "PolyglotPayloadGenerator",
        }
        assert set(payloads.__all__) == expected


class TestGeneratorInterface:
    """Test that all generators follow the same interface."""

    GENERATORS = [
        XSSPayloadGenerator,
        SQLiPayloadGenerator,
        SSTIPayloadGenerator,
        PolyglotPayloadGenerator,
    ]

    @pytest.mark.parametrize("generator_cls", GENERATORS)
    def test_has_vuln_type_property(self, generator_cls):
        """Each generator should have a vuln_type property."""
        gen = generator_cls() if generator_cls in [XSSPayloadGenerator, PolyglotPayloadGenerator] else generator_cls()
        assert hasattr(gen, "vuln_type")
        assert isinstance(gen.vuln_type, str)
        assert len(gen.vuln_type) > 0

    @pytest.mark.parametrize("generator_cls", GENERATORS)
    def test_generate_method_works(self, generator_cls):
        """Each generator's generate() method should work."""
        gen = generator_cls() if generator_cls in [XSSPayloadGenerator, PolyglotPayloadGenerator] else generator_cls()
        payloads = list(gen.generate("http://test.callback.com"))
        assert len(payloads) > 0

    @pytest.mark.parametrize("generator_cls", GENERATORS)
    def test_generate_returns_tuples(self, generator_cls):
        """Each generator should yield (payload, context) tuples."""
        gen = generator_cls() if generator_cls in [XSSPayloadGenerator, PolyglotPayloadGenerator] else generator_cls()
        for item in gen.generate("http://test.callback.com"):
            assert isinstance(item, tuple)
            assert len(item) == 2
            payload, context = item
            assert isinstance(payload, str)
            assert isinstance(context, str)


class TestTotalPayloadCount:
    """Test overall payload counts across all generators."""

    def test_minimum_total_payloads(self):
        """Total payloads should be at least 22 (5 XSS + 8 SQLi + 6 SSTI + 3 polyglot)."""
        xss = list(XSSPayloadGenerator().generate("http://test"))
        sqli = list(SQLiPayloadGenerator().generate("http://test"))
        ssti = list(SSTIPayloadGenerator().generate("http://test"))
        poly = list(PolyglotPayloadGenerator().generate("http://test"))

        total = len(xss) + len(sqli) + len(ssti) + len(poly)
        assert total >= 22, f"Expected at least 22 total payloads, got {total}"

    def test_each_generator_produces_expected_minimum(self):
        """Each generator should produce minimum expected payloads."""
        xss = list(XSSPayloadGenerator().generate("http://test"))
        sqli = list(SQLiPayloadGenerator().generate("http://test"))
        ssti = list(SSTIPayloadGenerator().generate("http://test"))
        poly = list(PolyglotPayloadGenerator().generate("http://test"))

        assert len(xss) >= 5, f"XSS: expected >= 5, got {len(xss)}"
        assert len(sqli) >= 8, f"SQLi: expected >= 8, got {len(sqli)}"
        assert len(ssti) >= 6, f"SSTI: expected >= 6, got {len(ssti)}"
        assert len(poly) == 3, f"Polyglot: expected 3, got {len(poly)}"


class TestVulnTypeUniqueness:
    """Test that each generator has a unique vuln_type."""

    def test_vuln_types_are_unique(self):
        """Each generator should have a distinct vuln_type."""
        generators = [
            XSSPayloadGenerator(),
            SQLiPayloadGenerator(),
            SSTIPayloadGenerator(),
            PolyglotPayloadGenerator(),
        ]

        vuln_types = [g.vuln_type for g in generators]
        assert len(vuln_types) == len(set(vuln_types)), f"Duplicate vuln_types: {vuln_types}"

    def test_expected_vuln_types(self):
        """Generators should have expected vuln_type values."""
        assert XSSPayloadGenerator().vuln_type == "xss"
        assert SQLiPayloadGenerator().vuln_type == "sqli"
        assert SSTIPayloadGenerator().vuln_type == "ssti"
        assert PolyglotPayloadGenerator().vuln_type == "polyglot"
