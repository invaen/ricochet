---
phase: 04-injection-engine
plan: 02
subsystem: injection
tags: [http-parsing, burp-suite, injection-vectors, urllib]

# Dependency graph
requires:
  - phase: 04-01
    provides: injection package structure and rate limiter
provides:
  - ParsedRequest dataclass for HTTP request representation
  - Burp-format request file parsing with CRLF handling
  - Injection vector extraction from query, headers, cookies, body
  - URL construction and parameter injection helpers
affects: [04-03 payload injection, 04-04 request modification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - http.client.parse_headers for RFC 5322 header parsing
    - dataclasses.replace for immutable modifications
    - urllib.parse for query string manipulation

key-files:
  created:
    - ricochet/injection/parser.py
    - ricochet/injection/vectors.py
  modified:
    - ricochet/injection/__init__.py

key-decisions:
  - "Bytes-first parsing for CRLF handling (Burp exports)"
  - "Top-level JSON strings only for v1 (recursive extraction future work)"
  - "INJECTABLE_HEADERS list for security-relevant header targeting"

patterns-established:
  - "InjectionVector as injection point abstraction"
  - "ParsedRequest as HTTP request data structure"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 4 Plan 2: Burp Request Parser & Vector Extractor Summary

**Burp-format HTTP request parser with automatic injection vector extraction across query params, headers, cookies, and body fields**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T04:20:02Z
- **Completed:** 2026-01-30T04:22:30Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- ParsedRequest dataclass representing raw HTTP request structure (method, path, headers, body, host)
- parse_request_file handling Burp export format with CRLF line endings
- extract_vectors identifying injection points in query, headers, cookies, form body, and JSON body
- build_url and inject_into_path for URL manipulation without mutation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Burp request file parser** - `c441ed5` (feat)
2. **Task 2: Create injection vector extractor** - `0cb0e68` (feat)
3. **Task 3: Add URL construction helper** - `ccf4cd5` (feat)

## Files Created/Modified

- `ricochet/injection/parser.py` - ParsedRequest dataclass, parse_request_file, parse_request_string, build_url, inject_into_path
- `ricochet/injection/vectors.py` - InjectionVector dataclass, extract_vectors, INJECTABLE_HEADERS
- `ricochet/injection/__init__.py` - Updated exports for all new functions

## Decisions Made

1. **Bytes-first parsing** - Accept bytes input to properly handle CRLF line endings from Burp exports
2. **INJECTABLE_HEADERS list** - Predefined security-relevant headers (User-Agent, X-Forwarded-For, etc.) for targeted header injection
3. **Top-level JSON only** - Extract only top-level string fields from JSON bodies; recursive extraction deferred to future work
4. **Immutable modifications** - inject_into_path uses dataclasses.replace() to avoid mutating original request

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Parser and vector extractor ready for payload injection engine
- ParsedRequest provides input format for request modification
- InjectionVector provides abstraction for targeting injection points
- Ready for 04-03 (payload generation) or request modification work

---
*Phase: 04-injection-engine*
*Completed: 2026-01-30*
