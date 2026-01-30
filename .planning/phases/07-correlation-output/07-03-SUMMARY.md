---
phase: 07-correlation-output
plan: 03
subsystem: injection
tags: [proxy, burp, zap, http-client, urllib]

# Dependency graph
requires:
  - phase: 04-injection-engine
    provides: send_request() HTTP client and Injector class
provides:
  - HTTP proxy routing via --proxy flag
  - Proxy support for Burp Suite and ZAP interception
affects: [08-polish-packaging, security-testing-workflow]

# Tech tracking
tech-stack:
  added: []
  patterns: [proxy-handler-chain]

key-files:
  created: []
  modified:
    - ricochet/injection/http_client.py
    - ricochet/injection/injector.py
    - ricochet/cli.py

key-decisions:
  - "ProxyHandler added before HTTPS handler in opener chain"
  - "Disable environment proxy detection when no --proxy specified"
  - "SSL verification already disabled by default in Injector"

patterns-established:
  - "Proxy support pattern: pass proxy_url through entire call chain"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 7 Plan 3: HTTP Proxy Support Summary

**HTTP proxy routing for Burp/ZAP interception via --proxy CLI flag using urllib.request.ProxyHandler**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T07:04:11Z
- **Completed:** 2026-01-30T07:06:XX
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- send_request() accepts optional proxy_url parameter
- Injector class wires proxy_url through to all HTTP requests
- CLI inject command has --proxy argument for Burp/ZAP interception
- Proxy support works in both standard inject and --from-crawl modes
- User notification when proxy is active

## Task Commits

Each task was committed atomically:

1. **Task 1: Add proxy_url parameter to send_request()** - `559baa3` (feat)
2. **Task 2: Add --proxy argument to inject command** - `c171b6f` (feat)

## Files Modified

- `ricochet/injection/http_client.py` - Added proxy_url parameter with ProxyHandler support
- `ricochet/injection/injector.py` - Added proxy_url to Injector class, pass to send_request()
- `ricochet/cli.py` - Added --proxy argument, wire through to Injector and crawl mode

## Decisions Made

- **ProxyHandler placement:** Added before HTTPS handler so proxy routing is configured first
- **Environment proxy isolation:** Disable environment proxy detection when no --proxy specified (prevents unexpected routing)
- **SSL verification:** Already disabled by default in Injector for security testing - proxy compatibility is automatic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Proxy support ready for security testing workflows
- Users can intercept all injection traffic through Burp Suite or ZAP
- Ready for 07-04 (structured output formatters) if planned

---
*Phase: 07-correlation-output*
*Completed: 2026-01-30*
