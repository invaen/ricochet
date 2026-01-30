---
phase: 01-foundation
plan: 02
subsystem: database
tags: [sqlite, persistence, correlation-id, python]

# Dependency graph
requires:
  - phase: 01-01
    provides: CLI skeleton with --db flag and subcommand structure
provides:
  - SQLite persistence layer at ~/.ricochet/ricochet.db
  - InjectionRecord dataclass for tracking injections
  - Correlation ID generator (16-char hex)
  - Foreign key enforcement between callbacks and injections
affects: [02-correlation, 03-inject, 04-listen]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SQLite with foreign key enforcement via PRAGMA
    - Dataclass for record types
    - secrets.token_hex for URL-safe IDs

key-files:
  created:
    - ricochet/core/correlation.py
    - ricochet/core/store.py
  modified:
    - ricochet/cli.py

key-decisions:
  - "16-char hex IDs (token_hex(8)) - URL-safe, collision-resistant"
  - "Foreign keys enforced via PRAGMA foreign_keys = ON"
  - "Store initialized on every CLI run (not lazy)"

patterns-established:
  - "InjectionStore singleton pattern per process"
  - "Connection acquired per operation (context manager)"
  - "Subcommand handlers receive (args, store) signature"

# Metrics
duration: 3 min
completed: 2026-01-30
---

# Phase 1 Plan 2: Database Persistence Summary

**SQLite persistence layer with correlation ID generation, injection/callback schema, and foreign key enforcement**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-30T02:54:55Z
- **Completed:** 2026-01-30T02:58:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created correlation ID generator producing 16-char hex strings (URL-safe, collision-resistant)
- Implemented InjectionStore with injections/callbacks tables and proper foreign key constraints
- Wired store initialization into CLI - database created at ~/.ricochet/ricochet.db on first run
- Records persist across program runs

## Task Commits

Each task was committed atomically:

1. **Task 1: Create correlation ID generator** - `f954401` (feat)
2. **Task 2: Create SQLite store** - `c355eb2` (feat)
3. **Task 3: Wire store initialization into CLI** - `be94d0e` (feat)

## Files Created/Modified

- `ricochet/core/correlation.py` - generate_correlation_id() function using secrets.token_hex(8)
- `ricochet/core/store.py` - InjectionStore class, InjectionRecord dataclass, get_db_path() function
- `ricochet/cli.py` - Added store initialization and subcommand handler signature update

## Decisions Made

- Used secrets.token_hex(8) for 16-char hex IDs - alphanumeric only, no URL encoding needed
- Foreign keys enforced via PRAGMA statement on every connection
- Store initialized eagerly on CLI startup (not lazy) to ensure DB exists
- Subcommand handlers will receive (args, store) to enable injection tracking

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Database persistence complete, ready for correlation engine (Phase 2)
- Schema supports injections and callbacks with foreign key relationship
- CLI ready for inject, listen, and correlate subcommands
- No blockers

---
*Phase: 01-foundation*
*Completed: 2026-01-30*
