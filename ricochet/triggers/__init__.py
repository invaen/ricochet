"""
Triggers module for second-order vulnerability detection.

Active triggering probes common execution contexts (admin panels, etc.).
Passive triggering polls for callbacks after injection.
"""

from ricochet.triggers.active import (
    ActiveTrigger,
    TRIGGER_ENDPOINTS,
    TriggerResult,
)
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
    # Active triggering
    "ActiveTrigger",
    "TRIGGER_ENDPOINTS",
    "TriggerResult",
    # Passive polling
    "PollingConfig",
    "PollingStrategy",
    "poll_for_callbacks",
    # Suggestions
    "TRIGGER_MAP",
    "TriggerSuggester",
    "TriggerSuggestion",
]
