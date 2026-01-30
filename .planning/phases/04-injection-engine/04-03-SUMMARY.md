---
phase: 04-injection-engine
plan: 03
subsystem: injection
tags: [cli, http-client, injection, rate-limiting, sqlite]

# Dependency graph
requires:
  - phase: 04-01
    provides: HTTP client and rate limiter
  - phase: 04-02
    provides: Request parser and vector extraction
provides:
  - Multi-vector injection orchestrator (Injector class)
  - CLI inject subcommand (-u URL, -r request.txt)
  - Callback placeholder substitution ({{CALLBACK}})
  - Database-tracked injections with correlation IDs
affects: [05-payload-library, 06-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dataclass-based results (InjectionResult)
    - Dry-run mode for safe testing
    - Lazy imports in CLI for fast startup

key-files:
  created:
    - ricochet/injection/injector.py
  modified:
    - ricochet/injection/__init__.py
    - ricochet/cli.py

key-decisions:
  - "Dry-run records injections to database (enables pre-flight verification)"
  - "SSL verification disabled by default for security testing targets"
  - "Parameter not found returns exit code 2 with available parameters listed"

patterns-established:
  - "Injection results as dataclasses with correlation tracking"
  - "CLI mutually exclusive groups for target specification"

# Metrics
duration: 3min
completed: 2026-01-30
---

# Phase 4 Plan 3: Injection Orchestrator & CLI Summary

**Multi-vector injection engine with CLI interface for URL/request-file injection, callback placeholder substitution, and database tracking**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-30T04:27:07Z
- **Completed:** 2026-01-30T04:29:42Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Injector class orchestrates payload injection across all vector types (query, header, cookie, body, json)
- CLI `inject` subcommand supports both URL mode (-u) and Burp request file mode (-r)
- {{CALLBACK}} placeholder substitution with unique correlation IDs per injection
- Database tracking enables callback correlation with injection context
- Dry-run mode for verifying injection plan without network activity

## Task Commits

Each task was committed atomically:

1. **Task 1: Create injection orchestrator** - `a50c80f` (feat)
2. **Task 2: Add inject subcommand to CLI** - `4f10fde` (feat)
3. **Task 3: End-to-end injection test** - `3dd786a` (chore)

## Files Created/Modified

- `ricochet/injection/injector.py` - Injector class, InjectionResult dataclass, substitute_callback()
- `ricochet/injection/__init__.py` - Export Injector, InjectionResult, substitute_callback
- `ricochet/cli.py` - inject subcommand with -u/-r/--param/--payload/--dry-run options

## Decisions Made

- **Dry-run records to database:** Enables pre-flight verification that injections are tracked correctly
- **SSL verification disabled by default:** Common pattern for security testing against internal/dev targets
- **Exit code 2 for missing param:** Consistent with argument error convention, lists available parameters

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Injection engine complete: users can inject via CLI with full database tracking
- Ready for Phase 5 (Payload Library) to provide pre-built payload templates
- Callback server (Phase 2/3) already running can correlate injections

---
*Phase: 04-injection-engine*
*Completed: 2026-01-30*
