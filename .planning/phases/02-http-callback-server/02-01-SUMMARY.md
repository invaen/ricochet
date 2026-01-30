---
phase: 02-http-callback-server
plan: 01
subsystem: server
tags: [http, threading, sqlite, callbacks, oob]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: InjectionStore, correlation ID generation, database schema
provides:
  - CallbackRecord dataclass for callback data
  - record_callback() method for persisting callbacks
  - get_callbacks_for_injection() and get_injections_with_callbacks() queries
  - CallbackServer (ThreadingHTTPServer subclass)
  - CallbackHandler with correlation ID extraction
  - run_callback_server() entry point
affects: [02-02 (CLI integration), 03-payload-generation, 05-correlation-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ThreadingHTTPServer with daemon_threads for concurrent requests
    - Signal handlers (SIGINT/SIGTERM) for graceful shutdown
    - TYPE_CHECKING imports for forward references

key-files:
  created:
    - ricochet/server/__init__.py
    - ricochet/server/http.py
  modified:
    - ricochet/core/store.py

key-decisions:
  - "Always return 200 OK to avoid leaking valid/invalid correlation IDs"
  - "Extract correlation ID from last non-empty URL path segment"
  - "Use 0.5s server timeout for responsive shutdown"

patterns-established:
  - "Handler._extract_correlation_id() validates 16-char lowercase hex"
  - "Server stores reference to InjectionStore for callback persistence"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 02 Plan 01: HTTP Callback Server Summary

**ThreadingHTTPServer-based callback capture with correlation ID extraction and SQLite persistence**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T03:21:24Z
- **Completed:** 2026-01-30T03:23:38Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Extended InjectionStore with callback recording and query methods
- Created HTTP callback server with ThreadingHTTPServer for concurrent request handling
- Implemented correlation ID extraction from any URL path position
- Added graceful shutdown via signal handlers

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend InjectionStore with callback methods** - `9a9c665` (feat)
2. **Task 2: Create HTTP callback server module** - `75d56fd` (feat)

## Files Created/Modified

- `ricochet/core/store.py` - Added CallbackRecord dataclass and three new methods
- `ricochet/server/__init__.py` - Package initialization
- `ricochet/server/http.py` - CallbackHandler, CallbackServer, run_callback_server()

## Decisions Made

- Return 200 OK for all requests regardless of correlation ID validity (prevents enumeration)
- Correlation ID extracted from last non-empty path segment (supports /any/path/{id})
- Server timeout set to 0.5s for responsive shutdown while maintaining performance

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- HTTP callback server ready for CLI integration (02-02)
- Store methods ready for correlation engine (Phase 3+)
- All HTTP methods supported (GET, POST, HEAD, PUT, DELETE, OPTIONS, PATCH)

---
*Phase: 02-http-callback-server*
*Completed: 2026-01-30*
