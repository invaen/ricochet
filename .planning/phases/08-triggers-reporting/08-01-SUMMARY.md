---
phase: 08-triggers-reporting
plan: 01
subsystem: triggers
tags: [polling, backoff, callbacks, passive-mode]

# Dependency graph
requires:
  - phase: 07-correlation-output
    provides: "InjectionStore.get_findings() for querying callbacks"
  - phase: 04-injection-engine
    provides: "cmd_inject for payload injection"
provides:
  - "PollingConfig dataclass with timing parameters"
  - "PollingStrategy class with exponential backoff"
  - "poll_for_callbacks() function for continuous monitoring"
  - "ricochet passive CLI command for inject-and-poll workflow"
affects: [08-02-active-triggers, 08-03-suggestions]

# Tech tracking
tech-stack:
  added: []
  patterns: ["exponential backoff with quiet threshold", "time.monotonic() for timing"]

key-files:
  created:
    - ricochet/triggers/__init__.py
    - ricochet/triggers/polling.py
    - tests/test_triggers_polling.py
  modified:
    - ricochet/cli.py

key-decisions:
  - "5-poll quiet threshold before backoff activates"
  - "time.monotonic() for timing (avoids clock drift)"
  - "Reuse cmd_inject for passive mode injection phase"

patterns-established:
  - "Backoff pattern: 5 quiet polls then factor * current up to max"
  - "Passive mode = inject + poll (two-phase execution)"

# Metrics
duration: 5min
completed: 2026-01-30
---

# Phase 8 Plan 1: Polling Infrastructure Summary

**Exponential backoff polling with 5-poll quiet threshold, base 5s to max 60s intervals, integrated into passive CLI mode**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-30T07:28:42Z
- **Completed:** 2026-01-30T07:34:05Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created ricochet/triggers/ module with polling infrastructure
- PollingStrategy class with exponential backoff (5 quiet polls trigger, 1.5x factor, 60s cap)
- Added `ricochet passive` CLI command that combines injection with continuous polling
- Comprehensive unit tests (15 tests) covering config, strategy, and poll_for_callbacks

## Task Commits

Each task was committed atomically:

1. **Task 1: Create polling module with PollingStrategy** - `2d0a098` (feat)
2. **Task 2: Add passive CLI subcommand** - `1b84af4` (feat)
3. **Task 3: Add unit tests for polling logic** - `91c7643` (test)

**Bug fix:** `b193948` (fix: add missing --param argument to passive parser)

## Files Created/Modified
- `ricochet/triggers/__init__.py` - Module exports (PollingConfig, PollingStrategy, poll_for_callbacks)
- `ricochet/triggers/polling.py` - Polling infrastructure with backoff logic
- `ricochet/cli.py` - Added passive subcommand with --poll-interval and --poll-timeout
- `tests/test_triggers_polling.py` - 15 unit tests for polling behavior

## Decisions Made
- **5-poll quiet threshold:** Avoids premature backoff while still adapting to quiet periods
- **time.monotonic() for timing:** Consistent with rate_limiter.py pattern, avoids clock drift
- **Reuse cmd_inject for passive mode:** DRY principle, single source of injection logic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing --param argument to passive parser**
- **Found during:** Verification (dry-run test)
- **Issue:** passive command reuses cmd_inject which requires args.param attribute
- **Fix:** Added -p/--param argument to passive_parser
- **Files modified:** ricochet/cli.py
- **Verification:** `ricochet passive -r /tmp/test.txt --dry-run` works correctly
- **Committed in:** b193948

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Minor fix required for cmd_inject compatibility. No scope creep.

## Issues Encountered
- Linter kept auto-generating files for future plans (active.py, suggestions.py) - removed them to avoid import errors

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Polling infrastructure complete and tested
- Ready for 08-02 (active trigger probing) and 08-03 (trigger suggestions)
- The triggers module can be extended with additional exports

---
*Phase: 08-triggers-reporting*
*Completed: 2026-01-30*
