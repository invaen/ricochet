---
phase: 08-triggers-reporting
plan: 02
subsystem: triggers
tags: [active-probing, endpoint-discovery, trigger-detection]

dependency-graph:
  requires: [01-foundation, 04-injection-engine]
  provides: [active-trigger-probing, endpoint-catalog]
  affects: []

tech-stack:
  added: []
  patterns: [rate-limited-probing, callback-based-progress]

key-files:
  created:
    - ricochet/triggers/active.py
    - tests/test_triggers_active.py
  modified:
    - ricochet/triggers/__init__.py
    - ricochet/cli.py

decisions:
  - id: "08-02-01"
    decision: "Default rate 2.0 req/s for active probing"
    rationale: "Slower than injection rate to avoid admin panel rate limits"

metrics:
  duration: 5 min
  completed: 2026-01-30
---

# Phase 8 Plan 02: Active Trigger Probing Summary

**One-liner:** Active endpoint probing with 28 common admin/support/analytics paths and rate-limited trigger detection

## What Was Built

### Active Trigger Module (`ricochet/triggers/active.py`)

- `TRIGGER_ENDPOINTS` list with 28 common second-order execution contexts:
  - Admin paths: /admin, /admin/users, /admin/logs, /dashboard, /manage
  - Support paths: /support, /tickets, /helpdesk, /feedback
  - Analytics: /analytics, /reports, /stats, /logs, /metrics
  - Content: /moderation, /content, /posts, /comments, /reviews
  - Export: /export, /download, /pdf, /report/generate, /print

- `TriggerResult` dataclass for probe results:
  - endpoint, status, error, response_size fields
  - Status is None on request failure

- `ActiveTrigger` class:
  - Rate-limited endpoint probing (default 2.0 req/s)
  - Configurable timeout and proxy support
  - `probe_endpoint()` for single endpoint
  - `probe_all()` with callback for progress reporting

### CLI Integration (`ricochet/cli.py`)

- `ricochet active` subcommand with options:
  - `-u/--url` (required): Base URL to probe
  - `--endpoints`: Custom endpoint list file
  - `--rate`: Request rate (default 2.0)
  - `--timeout`: Request timeout
  - `--proxy`: HTTP proxy URL

- Progress output with status icons:
  - `[+]` for 2xx responses (accessible)
  - `[-]` for 404 responses
  - `[*]` for other status codes
  - `[!]` for errors (timeout, connection)

### Test Suite (`tests/test_triggers_active.py`)

- 18 comprehensive tests covering:
  - TRIGGER_ENDPOINTS format and content
  - TriggerResult dataclass fields
  - ActiveTrigger URL normalization
  - Probe success/error handling
  - Custom endpoint support
  - Callback invocation
  - Proxy and timeout parameter passing

## Commits

| Hash | Description |
|------|-------------|
| d2d5734 | feat(08-02): add active trigger probing module |
| 22da648 | feat(08-02): add active CLI subcommand for endpoint probing |
| ec64685 | test(08-02): add unit tests for active trigger probing |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added cmd_suggest stub**
- **Found during:** Task 2
- **Issue:** CLI referenced cmd_suggest from 08-03 but function didn't exist
- **Fix:** Added placeholder cmd_suggest function to unblock CLI
- **Files modified:** ricochet/cli.py
- **Commit:** 22da648

**2. [Rule 3 - Blocking] Recreated active.py after concurrent overwrite**
- **Found during:** Task 3
- **Issue:** Concurrent 08-01 execution overwrote triggers/__init__.py, losing active exports
- **Fix:** Re-created active.py and updated __init__.py
- **Files modified:** ricochet/triggers/active.py, ricochet/triggers/__init__.py
- **Commit:** ec64685

## Verification

```bash
# Module imports
python -c "from ricochet.triggers import ActiveTrigger, TRIGGER_ENDPOINTS"
# OK

# CLI command available
python -m ricochet active --help | grep -E "(endpoints|rate)"
# Shows --endpoints and --rate options

# Tests pass
python -m pytest tests/test_triggers_active.py -v
# 18 passed

# Endpoint count
python -c "from ricochet.triggers.active import TRIGGER_ENDPOINTS; print(len(TRIGGER_ENDPOINTS))"
# 28
```

## Usage Example

```bash
# Probe default endpoints on target
ricochet active -u https://target.com

# Use custom endpoint list
ricochet active -u https://target.com --endpoints custom-paths.txt

# Slower rate for careful probing
ricochet active -u https://target.com --rate 0.5

# Through proxy
ricochet active -u https://target.com --proxy http://127.0.0.1:8080
```

## Next Phase Readiness

Plan 08-02 complete. Active trigger probing enables:
- Automated trigger detection for stored XSS
- Custom endpoint discovery workflows
- Integration with callback server for full second-order detection
