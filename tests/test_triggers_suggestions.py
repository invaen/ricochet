"""Tests for trigger suggestion engine."""

import pytest

from ricochet.core.store import InjectionRecord
from ricochet.triggers.suggestions import (
    TRIGGER_MAP,
    TriggerSuggester,
    TriggerSuggestion,
)


class TestTriggerSuggestion:
    """Tests for TriggerSuggestion dataclass."""

    def test_fields_accessible(self):
        """TriggerSuggestion fields are accessible."""
        sug = TriggerSuggestion(
            location="Test Location",
            likelihood="high",
            description="Test description",
            manual_steps=["Step 1", "Step 2"],
        )
        assert sug.location == "Test Location"
        assert sug.likelihood == "high"
        assert sug.description == "Test description"
        assert sug.manual_steps == ["Step 1", "Step 2"]


class TestTriggerMap:
    """Tests for TRIGGER_MAP constant."""

    def test_contains_expected_keys(self):
        """TRIGGER_MAP contains expected parameter keys."""
        expected_keys = ["name", "comment", "message", "email", "search"]
        for key in expected_keys:
            assert key in TRIGGER_MAP, f"Missing key: {key}"

    def test_values_are_lists_of_suggestions(self):
        """TRIGGER_MAP values are lists of TriggerSuggestion."""
        for key, value in TRIGGER_MAP.items():
            assert isinstance(value, list), f"{key} value is not a list"
            for item in value:
                assert isinstance(item, TriggerSuggestion), (
                    f"{key} contains non-TriggerSuggestion: {type(item)}"
                )

    def test_covers_at_least_7_patterns(self):
        """TRIGGER_MAP covers at least 7 parameter patterns."""
        assert len(TRIGGER_MAP) >= 7, f"Only {len(TRIGGER_MAP)} patterns defined"


class TestTriggerSuggester:
    """Tests for TriggerSuggester class."""

    @pytest.fixture
    def suggester(self):
        """Create a TriggerSuggester instance."""
        return TriggerSuggester()

    def test_get_suggestions_exact_match(self, suggester):
        """Returns suggestions for exact parameter match."""
        suggestions = suggester.get_suggestions("comment")
        assert len(suggestions) > 0
        assert suggestions[0].location == "Content Moderation Queue"

    def test_get_suggestions_fuzzy_match_user_name(self, suggester):
        """Returns suggestions for fuzzy match (user_name -> name)."""
        suggestions = suggester.get_suggestions("user_name")
        assert len(suggestions) > 0
        # Should match "name" pattern
        locations = [s.location for s in suggestions]
        assert "Admin User List" in locations

    def test_get_suggestions_fuzzy_match_username(self, suggester):
        """Returns suggestions for fuzzy match (username -> name)."""
        suggestions = suggester.get_suggestions("username")
        assert len(suggestions) > 0
        locations = [s.location for s in suggestions]
        assert "Admin User List" in locations

    def test_get_suggestions_fuzzy_match_first_name(self, suggester):
        """Returns suggestions for fuzzy match (first_name -> name)."""
        suggestions = suggester.get_suggestions("first_name")
        assert len(suggestions) > 0
        locations = [s.location for s in suggestions]
        assert "Admin User List" in locations

    def test_get_suggestions_unknown_parameter(self, suggester):
        """Returns empty list for unknown parameter."""
        suggestions = suggester.get_suggestions("xyz_completely_unknown_param")
        assert suggestions == []

    def test_get_suggestions_sorted_by_likelihood(self, suggester):
        """Results are sorted by likelihood (high before medium before low)."""
        # "name" has both high and medium suggestions
        suggestions = suggester.get_suggestions("name")
        assert len(suggestions) >= 2

        # Check order: high should come before medium
        likelihoods = [s.likelihood for s in suggestions]
        high_idx = likelihoods.index("high") if "high" in likelihoods else -1
        medium_idx = likelihoods.index("medium") if "medium" in likelihoods else len(likelihoods)

        if high_idx != -1:
            assert high_idx < medium_idx, "High should come before medium"

    def test_get_suggestions_deduplicates_by_location(self, suggester):
        """Results are deduplicated by location."""
        suggestions = suggester.get_suggestions("email")
        locations = [s.location for s in suggestions]
        # No duplicate locations
        assert len(locations) == len(set(locations))

    def test_get_suggestions_with_context_parameter(self, suggester):
        """Context parameter is accepted (for future use)."""
        # Should not raise an error
        suggestions = suggester.get_suggestions("comment", context="html")
        assert isinstance(suggestions, list)


class TestTriggerSuggesterForInjection:
    """Tests for TriggerSuggester.get_suggestions_for_injection."""

    @pytest.fixture
    def suggester(self):
        """Create a TriggerSuggester instance."""
        return TriggerSuggester()

    @pytest.fixture
    def injection_record(self):
        """Create a sample InjectionRecord."""
        return InjectionRecord(
            id="abc123",
            target_url="https://example.com/submit",
            parameter="comment",
            payload="<script>fetch('http://test.com')</script>",
            timestamp=1234567890.0,
            context="html",
        )

    def test_works_with_injection_record(self, suggester, injection_record):
        """Returns suggestions for an InjectionRecord."""
        suggestions = suggester.get_suggestions_for_injection(injection_record)
        assert len(suggestions) > 0
        assert suggestions[0].location == "Content Moderation Queue"

    def test_uses_parameter_field(self, suggester):
        """Uses injection.parameter field correctly."""
        injection = InjectionRecord(
            id="test123",
            target_url="https://example.com",
            parameter="user_name",
            payload="test",
            timestamp=0.0,
            context=None,
        )
        suggestions = suggester.get_suggestions_for_injection(injection)
        locations = [s.location for s in suggestions]
        assert "Admin User List" in locations

    def test_handles_unknown_parameter(self, suggester):
        """Handles injection with unknown parameter."""
        injection = InjectionRecord(
            id="test123",
            target_url="https://example.com",
            parameter="xyz_unknown",
            payload="test",
            timestamp=0.0,
            context=None,
        )
        suggestions = suggester.get_suggestions_for_injection(injection)
        assert suggestions == []


class TestCustomTriggerMap:
    """Tests for TriggerSuggester with custom trigger map."""

    def test_custom_trigger_map(self):
        """TriggerSuggester accepts custom trigger map."""
        custom_map = {
            "custom_param": [
                TriggerSuggestion(
                    location="Custom Location",
                    likelihood="high",
                    description="Custom description",
                    manual_steps=["Step 1"],
                )
            ]
        }
        suggester = TriggerSuggester(trigger_map=custom_map)
        suggestions = suggester.get_suggestions("custom_param")
        assert len(suggestions) == 1
        assert suggestions[0].location == "Custom Location"

    def test_custom_map_does_not_include_defaults(self):
        """Custom map replaces defaults, doesn't merge."""
        custom_map = {
            "custom_param": [
                TriggerSuggestion(
                    location="Custom Location",
                    likelihood="high",
                    description="Custom",
                    manual_steps=["Step 1"],
                )
            ]
        }
        suggester = TriggerSuggester(trigger_map=custom_map)
        # "comment" is in default map but not custom map
        suggestions = suggester.get_suggestions("comment")
        assert suggestions == []
