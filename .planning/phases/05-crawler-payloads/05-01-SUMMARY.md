---
phase: 05-crawler-payloads
plan: 01
subsystem: injection
tags: [crawler, html-parser, bfs, url-normalization, form-extraction]

# Dependency graph
requires:
  - phase: 04-injection-engine
    provides: HTTP client, rate limiter, injection infrastructure
provides:
  - Web crawler with BFS traversal and configurable depth/page limits
  - HTMLParser-based link and form extraction
  - URL normalization and same-domain filtering
  - Crawl vector export/import for inject workflow integration
  - CLI crawl subcommand with --export flag
  - CLI inject --from-crawl flag for crawl-based injection
affects: [phase-06-reporting, phase-07-monitoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - HTMLParser subclass for DOM extraction
    - BFS with deque for crawl traversal
    - Dataclass-based data transfer objects

key-files:
  created:
    - ricochet/injection/crawler.py
  modified:
    - ricochet/injection/__init__.py
    - ricochet/cli.py

key-decisions:
  - "HTMLParser over regex for robust HTML parsing"
  - "BFS over DFS for breadth-first discovery (finds more forms at shallow depth)"
  - "CrawlVector dataclass for portable injection point representation"
  - "Skip binary extensions early to avoid wasted requests"
  - "Same-domain filtering to prevent crawl scope creep"

patterns-established:
  - "Export/import JSON workflow for crawl-to-inject pipeline"
  - "Lazy import of heavy modules in CLI handlers"

# Metrics
duration: 4min
completed: 2026-01-30
---

# Phase 5 Plan 1: Web Crawler Summary

**HTMLParser-based web crawler with BFS traversal, form extraction, and CLI integration for automated injection point discovery**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-30T06:01:56Z
- **Completed:** 2026-01-30T06:05:27Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created LinkFormExtractor using stdlib HTMLParser for robust HTML parsing
- Implemented Crawler class with configurable depth, page limits, and rate limiting
- Added URL helpers for normalization, same-domain checks, and binary file filtering
- Integrated crawl subcommand with --export for vector serialization
- Added inject --from-crawl for seamless crawl-to-inject workflow

## Task Commits

Each task was committed atomically:

1. **Task 1: Create crawler module with HTMLParser-based extraction** - `b026376` (feat)
2. **Task 2: Add crawl subcommand with --export and inject --from-crawl flag** - `a08eeaf` (feat)
3. **Task 3: Verify crawler parsing and URL helpers** - verification only, no code changes

## Files Created/Modified

- `ricochet/injection/crawler.py` - New crawler module with LinkFormExtractor, Crawler, and export/import functions
- `ricochet/injection/__init__.py` - Added crawler exports to module public API
- `ricochet/cli.py` - Added cmd_crawl, _cmd_inject_from_crawl, and CLI argument configuration

## Decisions Made

- **HTMLParser over regex**: stdlib HTMLParser provides robust parsing of malformed HTML without external dependencies
- **BFS traversal**: Breadth-first search discovers more forms at shallow depths before hitting page limits
- **CrawlVector dataclass**: Portable JSON-serializable representation of injection points separate from request parsing
- **Binary extension filtering**: Skip .jpg, .pdf, .css, .js etc. early to avoid wasted HTTP requests
- **Same-domain filtering**: Prevent crawl scope from expanding to external sites

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Crawler ready for integration testing with real targets
- Export/import workflow enables batch injection operations
- Plan 05-02 (payload file loading) can proceed independently

---
*Phase: 05-crawler-payloads*
*Completed: 2026-01-30*
