---
phase: 05-crawler-payloads
plan: 02
subsystem: injection
tags: [payloads, wordlists, SecLists, Wfuzz, file-loading]

# Dependency graph
requires:
  - phase: 04-injection-engine
    provides: Injector class with inject_vector and inject_all_vectors methods
provides:
  - load_payloads function for batch payload loading
  - load_payloads_streaming generator for large files
  - --payloads CLI flag for file-based payload injection
affects: [06-vulnerability-payloads, 08-triggers-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generator pattern for memory-efficient file iteration"
    - "Lazy imports for fast CLI startup"

key-files:
  created:
    - ricochet/injection/payloads.py
  modified:
    - ricochet/injection/__init__.py
    - ricochet/cli.py

key-decisions:
  - "Strip only trailing newlines to preserve payload whitespace"
  - "Comment lines start with # (standard wordlist format)"
  - "UTF-8 encoding required for payload files"

patterns-established:
  - "Wordlist format: one payload per line, # comments, blank lines skipped"
  - "Dual API: list version and streaming generator"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 5 Plan 2: Custom Payload File Loading Summary

**Payload file loading with SecLists/Wfuzz compatibility and --payloads CLI flag for batch injection**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T06:02:09Z
- **Completed:** 2026-01-30T06:04:16Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created payload loading module with list and streaming APIs
- Added --payloads flag to inject command for file-based payload loading
- Maintained backward compatibility with single --payload flag
- Each payload gets unique correlation ID during injection

## Task Commits

Each task was committed atomically:

1. **Task 1: Create payload loading module** - `9f9cfc8` (feat)
2. **Task 2: Add --payloads flag to inject command** - `7a2ab9f` (feat)
3. **Task 3: Verify payload file loading** - No commit (verification only)

**Plan metadata:** Pending

## Files Created/Modified
- `ricochet/injection/payloads.py` - Payload file loading with load_payloads and load_payloads_streaming
- `ricochet/injection/__init__.py` - Exports load_payloads and load_payloads_streaming
- `ricochet/cli.py` - Added --payloads argument and multi-payload injection logic

## Decisions Made
- [05-02]: Strip only trailing newlines (rstrip) to preserve leading whitespace in payloads
- [05-02]: Comments must start with # as first character (standard wordlist convention)
- [05-02]: Lazy import of load_payloads in CLI for fast startup
- [05-02]: Empty payload files return 0 with warning (not an error)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Payload loading complete and integrated with CLI
- Ready for Phase 6 (Vulnerability Payloads) which will use this to load XSS/SQLi/SSTI payloads
- Ready for Phase 8 (Triggers & Reporting) which may load trigger payloads from files

---
*Phase: 05-crawler-payloads*
*Completed: 2026-01-30*
