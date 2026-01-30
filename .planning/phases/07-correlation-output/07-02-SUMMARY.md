---
phase: 07-correlation-output
plan: 02
subsystem: cli
tags: [jsonl, logging, argparse, findings, output]

requires:
  - phase: 07-01
    provides: Finding dataclass with severity property
provides:
  - output_json() function for JSONL output
  - output_text() function for human-readable output
  - findings CLI subcommand with filtering
  - Verbosity-based logging configuration
affects: [08-polish]

tech-stack:
  added: []
  patterns: [jsonl-output, severity-icons, verbosity-logging]

key-files:
  created:
    - ricochet/output/formatters.py
  modified:
    - ricochet/output/__init__.py
    - ricochet/cli.py

key-decisions:
  - "JSONL format (one JSON object per line) for pipeline compatibility"
  - "Severity icons: [!]=high, [+]=medium, [*]=low, [-]=info"
  - "Logs to stderr, findings to stdout for stream separation"

patterns-established:
  - "Verbosity mapping: 0->WARNING, 1->INFO, 2+->DEBUG"
  - "Verbose mode shows full payload and callback details"

duration: 2min
completed: 2026-01-30
---

# Phase 7 Plan 2: Output Formatters Summary

**JSONL and text formatters with findings CLI subcommand and verbosity-based logging**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T01:10:00Z
- **Completed:** 2026-01-30T01:12:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created output_json() for JSONL format (one record per line, pipeline-friendly)
- Created output_text() for human-readable format with severity icons
- Added findings subcommand with -o, --since, --min-severity options
- Configured logging based on -v flag count

## Task Commits

Each task was committed atomically:

1. **Task 1: Create output formatters** - `7d35e0a` (feat)
2. **Task 2: Add findings subcommand** - `1ea81bd` (feat)
3. **Task 3: Configure logging** - `d541097` (feat)

## Files Created/Modified
- `ricochet/output/formatters.py` - JSONL and text output formatters
- `ricochet/output/__init__.py` - Export formatters from module
- `ricochet/cli.py` - findings subcommand and setup_logging()

## Decisions Made
- JSONL format for JSON output (one record per line for streaming/piping)
- Severity icons for text: [!]=high, [+]=medium, [*]=low, [-]=info
- Logs go to stderr, findings go to stdout (stream separation)
- Verbosity levels: 0->WARNING, 1->INFO, 2+->DEBUG

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Output formatters complete and exported
- findings command available for viewing correlated findings
- Ready for Phase 8 polish work (error messages, help text refinement)

---
*Phase: 07-correlation-output*
*Completed: 2026-01-30*
