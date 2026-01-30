# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-29)

**Core value:** Detect vulnerabilities that execute in a different context than where they were injected
**Current focus:** Phase 7 - Correlation & Output

## Current Position

Phase: 7 of 8 (Correlation & Output)
Plan: 3 of 3 in current phase
Status: In progress
Last activity: 2026-01-30 - Completed 07-03-PLAN.md

Progress: [██████████████████████████░░░░] 83%

## Performance Metrics

**Velocity:**
- Total plans completed: 19
- Average duration: 2.3 min
- Total execution time: 43 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 2/2 | 5 min | 2.5 min |
| 2 | 2/2 | 4 min | 2.0 min |
| 3 | 2/2 | 4 min | 2.0 min |
| 4 | 3/3 | 12 min | 4.0 min |
| 5 | 2/2 | 4 min | 2.0 min |
| 6 | 4/4 | 8 min | 2.0 min |
| 7 | 3/3 | 6 min | 2.0 min |

**Recent Trend:**
- Last 5 plans: 2, 2, 2, 2, 2 min
- Trend: Consistent 2 min for correlation and generators

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 8 phases derived from 27 requirements following research-suggested ordering
- [Roadmap]: Correlation engine built in Phase 2 (critical path per research)
- [01-01]: Version defined in __init__.py, imported elsewhere
- [01-01]: Exit 0 when no command given (shows help)
- [01-02]: 16-char hex IDs (token_hex(8)) - URL-safe, collision-resistant
- [01-02]: Foreign keys enforced via PRAGMA foreign_keys = ON
- [02-01]: Return 200 OK for all requests to prevent correlation ID enumeration
- [02-01]: Extract correlation ID from last non-empty URL path segment
- [02-01]: 0.5s server timeout for responsive shutdown
- [02-02]: Lazy import of server module for fast CLI startup
- [02-02]: Exit code 2 for missing --http flag (argument error)
- [03-01]: Extract correlation ID from first subdomain label for DNS callbacks
- [03-01]: Always respond with 127.0.0.1 for A queries (prevents enumeration)
- [03-01]: Default DNS port 5353 (high port, no root required)
- [03-02]: No RSA+AES encryption - Interactsh public servers unsupported, self-hosted only
- [03-02]: Placeholder injection records for tracking external callback URLs
- [04-01]: Use time.monotonic() for rate limiting (avoids clock drift)
- [04-01]: Release lock while sleeping for thread efficiency
- [04-01]: Return HttpResponse for 4xx/5xx (not exceptions)
- [04-02]: Bytes-first parsing for CRLF handling (Burp exports)
- [04-02]: Top-level JSON strings only for v1 (recursive extraction future work)
- [04-02]: INJECTABLE_HEADERS list for security-relevant header targeting
- [04-03]: Dry-run records injections to database (enables pre-flight verification)
- [04-03]: SSL verification disabled by default for security testing targets
- [04-03]: Parameter not found returns exit code 2 with available parameters listed
- [05-01]: HTMLParser over regex for robust HTML parsing (stdlib, no deps)
- [05-01]: BFS crawl traversal for breadth-first form discovery
- [05-01]: CrawlVector dataclass for portable injection point representation
- [05-01]: Skip binary extensions early to avoid wasted requests
- [05-01]: Same-domain filtering to prevent crawl scope creep
- [05-02]: Strip only trailing newlines to preserve payload whitespace
- [05-02]: Comments start with # (standard wordlist convention)
- [05-02]: Lazy import of load_payloads for fast CLI startup
- [05-02]: Empty payload files return 0 with warning (not error)
- [06-01]: Context hint 'html' returned with all XSS payloads
- [06-01]: Generator yields raw payloads with {{CALLBACK}} placeholder (substitution in Injector)
- [06-03]: Engine parameter for targeted vs broad SSTI testing
- [06-03]: curl/nslookup command pairs for HTTP and DNS callbacks
- [06-04]: Context "universal" for polyglots (works across contexts)
- [06-04]: SSTI polyglot from Hackmanit research (51/51 engines)
- [06-04]: SQLi polyglot uses time-based (not OOB) for broader compatibility
- [07-01]: Severity derived from context property (not stored) - enables dynamic updates
- [07-01]: Post-query severity filtering - keeps SQL simple, filter in Python
- [07-03]: ProxyHandler added before HTTPS handler in opener chain
- [07-03]: Disable environment proxy detection when no --proxy specified

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-01-30
Stopped at: Completed 07-03-PLAN.md
Resume file: None
