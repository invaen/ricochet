---
phase: 08
plan: 03
subsystem: triggers
tags: [suggestions, context-mapping, cli]
dependency-graph:
  requires: [08-01]
  provides: [trigger-suggestions, suggest-cli]
  affects: []
tech-stack:
  added: []
  patterns: [context-mapping, fuzzy-matching]
key-files:
  created:
    - ricochet/triggers/suggestions.py
    - tests/test_triggers_suggestions.py
  modified:
    - ricochet/triggers/__init__.py
    - ricochet/cli.py
decisions:
  - id: "08-03-1"
    choice: "Fuzzy parameter matching via substring normalization"
    reason: "user_name, username, first_name all match name pattern without complex regex"
  - id: "08-03-2"
    choice: "10 parameter patterns in TRIGGER_MAP"
    reason: "Covers common injection points: name, comment, message, email, search, title, description, filename, user-agent, referer"
  - id: "08-03-3"
    choice: "Deduplication by location in suggestions"
    reason: "Prevents repetitive output when multiple patterns match same location"
metrics:
  duration: "6 min"
  completed: "2026-01-30"
---

# Phase 8 Plan 3: Trigger Suggestions Summary

**One-liner:** Context-aware trigger suggestions with fuzzy parameter matching and 10 common patterns covering admin panels, moderation queues, and log viewers.

## What Was Built

### TriggerSuggester Engine
- `TriggerSuggestion` dataclass with location, likelihood, description, manual_steps
- `TRIGGER_MAP` with 10 parameter patterns:
  - name, comment, message, email, search (original)
  - title, description, filename, user-agent, referer (added)
- `TriggerSuggester` class with fuzzy matching:
  - Normalizes parameters: strips underscores/hyphens, lowercase
  - Bidirectional substring matching: pattern in param OR param in pattern
  - Results sorted by likelihood (high > medium > low)
  - Deduplicates by location

### CLI suggest Subcommand
- `--param`: Show suggestions for any parameter name
- `--correlation-id`: Show suggestions for specific injection from database
- `--recent N`: Show suggestions for N most recent injections (default 10)

### Test Coverage
- 17 unit tests covering:
  - TriggerSuggestion dataclass
  - TRIGGER_MAP structure and minimum coverage
  - Exact and fuzzy parameter matching
  - Likelihood sorting
  - Location deduplication
  - InjectionRecord integration
  - Custom trigger map support

## Key Files

| File | Purpose |
|------|---------|
| `ricochet/triggers/suggestions.py` | TriggerSuggester, TriggerSuggestion, TRIGGER_MAP |
| `ricochet/triggers/__init__.py` | Module exports (updated) |
| `ricochet/cli.py` | cmd_suggest handler |
| `tests/test_triggers_suggestions.py` | 17 unit tests |

## Verification Results

```
# Module imports
from ricochet.triggers import TriggerSuggester, TriggerSuggestion, TRIGGER_MAP  # OK

# CLI works
ricochet suggest --param comment
[HIGH] Content Moderation Queue
  Comments typically reviewed before publishing
  Steps:
    1. Access moderation dashboard
    2. Review pending comments
    3. View comment detail page

# Fuzzy matching
ricochet suggest --param username
[HIGH] Admin User List
[MEDIUM] Activity Logs

# Tests
17 passed in 0.02s
```

## Decisions Made

1. **Fuzzy matching strategy**: Normalize by removing underscores/hyphens and lowercase, then check bidirectional substring containment. Simple and effective.

2. **10 patterns minimum**: Added title, description, filename beyond original 7 to cover CMS/file management use cases.

3. **Deduplication**: If "email" matches both "email" pattern and "name" pattern (via substring), deduplicate by location to avoid repetitive suggestions.

## Deviations from Plan

None - plan executed exactly as written.

## Integration Points

- Uses `InjectionRecord` from `ricochet.core.store` for parameter context
- Uses `InjectionStore.list_injections()` for recent injections lookup
- Exports via `ricochet.triggers` module alongside polling and active triggers

## Next Phase Readiness

Plan 08-03 complete. Trigger suggestions are available via CLI and programmatic API. Ready for Plan 08-04 (HTML report generation) or other Phase 8 plans.
