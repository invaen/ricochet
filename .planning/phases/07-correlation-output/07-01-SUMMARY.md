---
phase: 07-correlation-output
plan: 01
subsystem: database
tags: [sqlite, correlation, dataclass, findings]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: InjectionStore with injections/callbacks tables
provides:
  - Finding dataclass with severity derivation
  - get_findings() INNER JOIN correlation query
affects: [07-02, 07-03, 08-cli-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [derived-property-severity, post-query-filtering]

key-files:
  created:
    - ricochet/output/__init__.py
    - ricochet/output/finding.py
  modified:
    - ricochet/core/store.py

key-decisions:
  - "Severity derived from context property (not stored) - enables dynamic updates"
  - "Post-query severity filtering - allows SQL to remain simple, filter in Python"

patterns-established:
  - "Output module: ricochet/output/ for result formatting"
  - "Derived properties on dataclasses for computed values"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 7 Plan 01: Correlation Engine Summary

**Finding dataclass with severity derivation and get_findings() INNER JOIN query correlating injections to callbacks**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T07:04:15Z
- **Completed:** 2026-01-30T07:05:55Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created new output module with Finding dataclass
- Severity property auto-derives from context (ssti/sqli=high, xss=medium, other=info)
- get_findings() correlates injections with callbacks via INNER JOIN
- Filtering by timestamp (since) and minimum severity level

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Finding dataclass in new output module** - `4b4e07b` (feat)
2. **Task 2: Add get_findings() correlation query to InjectionStore** - `f95bacf` (feat)

## Files Created/Modified
- `ricochet/output/__init__.py` - Output module exports
- `ricochet/output/finding.py` - Finding dataclass with severity derivation
- `ricochet/core/store.py` - Added get_findings() correlation query

## Decisions Made
- Severity derived at property-access time (not stored in DB) - allows context classification updates without schema changes
- Post-query filtering for min_severity - keeps SQL simple, filter happens in Python after Finding objects created

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Finding dataclass ready for output formatting (07-02)
- Correlation query ready for CLI integration (07-03)
- All success criteria met:
  - Tool can identify which injection triggered a callback (via correlation_id)
  - Finding includes both injection and callback details
  - Severity derived from context

---
*Phase: 07-correlation-output*
*Completed: 2026-01-30*
