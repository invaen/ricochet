"""Trigger suggestion engine based on injection context.

Provides intelligent suggestions for where second-order vulnerabilities
might execute based on the parameter name and injection context.
"""

from dataclasses import dataclass
from typing import Literal, Optional

from ricochet.core.store import InjectionRecord


@dataclass
class TriggerSuggestion:
    """A suggested location where injected payload might execute."""
    location: str
    likelihood: Literal['high', 'medium', 'low']
    description: str
    manual_steps: list[str]


# Map parameter patterns to likely trigger locations
TRIGGER_MAP: dict[str, list[TriggerSuggestion]] = {
    'name': [
        TriggerSuggestion(
            location="Admin User List",
            likelihood="high",
            description="User names often displayed in admin dashboards",
            manual_steps=[
                "Log into admin panel",
                "Navigate to User Management",
                "View user list or search for injected user"
            ]
        ),
        TriggerSuggestion(
            location="Activity Logs",
            likelihood="medium",
            description="User activity may be logged with name field",
            manual_steps=[
                "Access activity/audit log viewer",
                "Filter by recent activity",
                "Review entries containing injected data"
            ]
        ),
    ],
    'comment': [
        TriggerSuggestion(
            location="Content Moderation Queue",
            likelihood="high",
            description="Comments typically reviewed before publishing",
            manual_steps=[
                "Access moderation dashboard",
                "Review pending comments",
                "View comment detail page"
            ]
        ),
    ],
    'message': [
        TriggerSuggestion(
            location="Support Ticket Dashboard",
            likelihood="high",
            description="Messages often reviewed by support staff",
            manual_steps=[
                "Access support/helpdesk dashboard",
                "View pending tickets",
                "Open ticket detail"
            ]
        ),
    ],
    'user-agent': [
        TriggerSuggestion(
            location="Analytics Dashboard",
            likelihood="medium",
            description="User-Agent strings logged for analytics",
            manual_steps=[
                "Access analytics or reporting dashboard",
                "View visitor/session details",
                "Check raw request logs"
            ]
        ),
    ],
    'referer': [
        TriggerSuggestion(
            location="Access Logs Viewer",
            likelihood="medium",
            description="Referer headers displayed in admin logs",
            manual_steps=[
                "Access admin log viewer",
                "Filter by recent requests",
                "View request details"
            ]
        ),
    ],
    'email': [
        TriggerSuggestion(
            location="Admin User List",
            likelihood="high",
            description="Email addresses displayed in user management",
            manual_steps=[
                "Access admin panel",
                "Navigate to user list",
                "Search or filter by email"
            ]
        ),
    ],
    'search': [
        TriggerSuggestion(
            location="Search Analytics",
            likelihood="medium",
            description="Search queries often logged for analytics",
            manual_steps=[
                "Access search analytics dashboard",
                "View popular/recent searches",
                "Check search logs"
            ]
        ),
    ],
    'title': [
        TriggerSuggestion(
            location="Content List Page",
            likelihood="high",
            description="Titles displayed in content management lists",
            manual_steps=[
                "Access admin/CMS dashboard",
                "View content list",
                "Check detail page"
            ]
        ),
    ],
    'description': [
        TriggerSuggestion(
            location="Content Preview",
            likelihood="medium",
            description="Descriptions shown in content listings",
            manual_steps=[
                "Access content management",
                "View list or search results",
                "Check detail/preview page"
            ]
        ),
    ],
    'filename': [
        TriggerSuggestion(
            location="File Manager",
            likelihood="high",
            description="Filenames displayed in file listing",
            manual_steps=[
                "Access file manager or media library",
                "View uploaded files list",
                "Check file details"
            ]
        ),
    ],
}

# Likelihood ordering for sorting
_LIKELIHOOD_ORDER = {'high': 0, 'medium': 1, 'low': 2}


class TriggerSuggester:
    """Provides trigger location suggestions based on injection context."""

    def __init__(self, trigger_map: Optional[dict[str, list[TriggerSuggestion]]] = None):
        """Initialize suggester with optional custom trigger map.

        Args:
            trigger_map: Custom map of parameter patterns to suggestions.
                        Defaults to built-in TRIGGER_MAP.
        """
        self.trigger_map = trigger_map if trigger_map is not None else TRIGGER_MAP

    def get_suggestions(
        self,
        parameter: str,
        context: Optional[str] = None
    ) -> list[TriggerSuggestion]:
        """Get trigger suggestions for a parameter.

        Performs fuzzy matching: "user_name", "username", "first_name" all
        match the "name" pattern.

        Args:
            parameter: Parameter name (e.g., "comment", "user_name")
            context: Optional injection context for additional matching

        Returns:
            List of TriggerSuggestion sorted by likelihood (high first)
        """
        suggestions: list[TriggerSuggestion] = []
        param_lower = parameter.lower().replace('_', '').replace('-', '')

        # Check each pattern for substring match
        for pattern, pattern_suggestions in self.trigger_map.items():
            pattern_normalized = pattern.lower().replace('_', '').replace('-', '')

            # Fuzzy match: pattern contained in param or param contained in pattern
            if pattern_normalized in param_lower or param_lower in pattern_normalized:
                suggestions.extend(pattern_suggestions)

        # Deduplicate by location (keep first occurrence)
        seen_locations: set[str] = set()
        unique_suggestions: list[TriggerSuggestion] = []
        for sug in suggestions:
            if sug.location not in seen_locations:
                seen_locations.add(sug.location)
                unique_suggestions.append(sug)

        # Sort by likelihood
        unique_suggestions.sort(key=lambda s: _LIKELIHOOD_ORDER.get(s.likelihood, 99))

        return unique_suggestions

    def get_suggestions_for_injection(
        self,
        injection: InjectionRecord
    ) -> list[TriggerSuggestion]:
        """Get trigger suggestions for an injection record.

        Args:
            injection: InjectionRecord with parameter and context fields

        Returns:
            List of TriggerSuggestion sorted by likelihood
        """
        return self.get_suggestions(injection.parameter, injection.context)
