---
phase: 02-http-callback-server
plan: 02
subsystem: cli
tags: [argparse, http-server, cli-integration]

# Dependency graph
requires:
  - phase: 02-01
    provides: HTTP callback server module with run_callback_server function
provides:
  - listen subcommand in CLI
  - --http, --host, --port flags for server configuration
  - Lazy import of server module for optimal startup
affects: [03-payload-generation, 04-injection-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy import pattern for optional dependencies
    - Subcommand handler pattern with func attribute

key-files:
  created: []
  modified:
    - ricochet/cli.py

key-decisions:
  - "Lazy import of server module - only load when listen --http is used"
  - "Exit code 2 for missing --http flag (argument error)"
  - "Default host 0.0.0.0 for accepting external connections"

patterns-established:
  - "Subcommand function naming: cmd_{subcommand}"
  - "Subcommand dispatch via set_defaults(func=cmd_X)"

# Metrics
duration: 2 min
completed: 2026-01-30
---

# Phase 02 Plan 02: CLI Integration Summary

**Wire HTTP callback server to CLI with listen subcommand and configurable host/port options**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T03:25:33Z
- **Completed:** 2026-01-30T03:27:12Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `listen` subcommand with --http, --host, --port options
- Implemented cmd_listen handler with lazy import of server module
- Verified end-to-end flow: CLI -> server -> callback -> database persistence
- Confirmed graceful shutdown via Ctrl+C (SIGINT)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add listen subcommand to CLI** - `2c905a4` (feat)
2. **Task 2: End-to-end verification** - No commit (verification only)

**Plan metadata:** Pending

## Files Created/Modified

- `ricochet/cli.py` - Added listen subparser and cmd_listen function

## Decisions Made

- Lazy import of `run_callback_server` - only loaded when --http is specified, keeping CLI startup fast
- Exit code 2 for missing --http flag - consistent with argument error conventions
- Default host 0.0.0.0 - allows external connections for real-world OOB testing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 complete - HTTP callback server fully integrated
- Users can now run `ricochet listen --http` to start capturing callbacks
- Database persistence verified - callbacks are recorded when correlation ID matches
- Ready for Phase 3: Payload Generation

---
*Phase: 02-http-callback-server*
*Completed: 2026-01-30*
