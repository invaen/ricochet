---
phase: 03-dns-external-callbacks
plan: 01
subsystem: server
tags: [dns, udp, socketserver, callbacks]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: InjectionStore for callback persistence
  - phase: 02-http-callback-server
    provides: Pattern for callback server implementation
provides:
  - DNS callback server capturing correlation IDs from subdomain queries
  - CLI --dns flag for starting DNS server
  - Response to all DNS queries (prevents enumeration)
affects: [payload-generation, burp-integration, documentation]

# Tech tracking
tech-stack:
  added: []
  patterns: [udp-server-pattern, dns-packet-parsing]

key-files:
  created: [ricochet/server/dns.py]
  modified: [ricochet/cli.py]

key-decisions:
  - "Extract correlation ID from first subdomain label"
  - "Always respond with 127.0.0.1 for A queries (prevents enumeration)"
  - "Default port 5353 (high port, no root required)"
  - "Store DNS callbacks with request_path='DNS:{qname}'"

patterns-established:
  - "DNS correlation via subdomain label: {correlation_id}.callback.domain.tld"
  - "Server protocol modules follow same signature: run_*_server(host, port, store)"

# Metrics
duration: 2min
completed: 2026-01-30
---

# Phase 3 Plan 1: DNS Callback Server Summary

**Stdlib-only DNS callback server capturing correlation IDs from subdomain queries using socketserver.UDPServer**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-30T03:52:26Z
- **Completed:** 2026-01-30T03:54:23Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- DNS callback server module with ThreadingMixIn for concurrent queries
- Correlation ID extraction from first subdomain label (16-char hex)
- Always responds to DNS queries with 127.0.0.1 (prevents enumeration, stops client retries)
- CLI --dns and --dns-port flags for starting DNS server

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DNS callback server module** - `0d6aedc` (feat)
2. **Task 2: Wire DNS server to CLI** - `a938243` (feat)
3. **Task 3: End-to-end DNS callback verification** - `897913c` (test)

## Files Created/Modified
- `ricochet/server/dns.py` - DNS callback server with DNSHandler, DNSCallbackServer, run_dns_server
- `ricochet/cli.py` - Added --dns and --dns-port flags to listen subcommand

## Decisions Made
- Extract correlation ID from first subdomain label (enables subdomain-based callbacks)
- Always respond with 127.0.0.1 for A queries (prevents enumeration via timing/error responses)
- Default port 5353 (high port, no root required for testing)
- Store DNS callbacks with request_path="DNS:{qname}" and headers={"qtype": str(qtype)}

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DNS callback server ready for payload generation integration
- Both HTTP and DNS callback mechanisms now available
- External callback integration (Interactsh) can proceed in parallel

---
*Phase: 03-dns-external-callbacks*
*Completed: 2026-01-30*
