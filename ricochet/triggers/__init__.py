"""
Triggers module for second-order vulnerability detection.

Passive triggering polls for callbacks after injection.
Active triggering (future) probes common execution contexts.
"""

from ricochet.triggers.polling import (
    PollingConfig,
    PollingStrategy,
    poll_for_callbacks,
)
from ricochet.triggers.suggestions import (
    TRIGGER_MAP,
    TriggerSuggester,
    TriggerSuggestion,
)

__all__ = [
    # Passive polling
    "PollingConfig",
    "PollingStrategy",
    "poll_for_callbacks",
    # Suggestions
    "TRIGGER_MAP",
    "TriggerSuggester",
    "TriggerSuggestion",
]
