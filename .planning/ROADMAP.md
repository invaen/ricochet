# Roadmap: Ricochet

## Overview

Ricochet progresses from foundational infrastructure through increasingly sophisticated detection capabilities. The journey starts with the correlation engine (the critical path for second-order detection), builds callback servers, adds injection mechanisms, implements payload generation, and culminates with trigger mechanisms and bug bounty reporting. Each phase delivers a testable capability that builds toward detecting vulnerabilities that execute in different contexts than where they were injected.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - CLI skeleton, SQLite persistence, zero-deps architecture
- [ ] **Phase 2: HTTP Callback Server** - Correlation IDs, built-in HTTP callback listener
- [ ] **Phase 3: DNS & External Callbacks** - DNS callback server, Interactsh integration
- [ ] **Phase 4: Injection Engine** - HTTP client, request parsing, Burp format support
- [ ] **Phase 5: Crawler & Payloads** - Auto-discovery crawling, custom payload loading
- [ ] **Phase 6: Vulnerability Payloads** - XSS, SQLi, SSTI payload generation with polyglots
- [ ] **Phase 7: Correlation & Output** - Match callbacks to injections, JSON/text/verbose output
- [ ] **Phase 8: Triggers & Reporting** - Passive/active trigger modes, bug bounty reports

## Phase Details

### Phase 1: Foundation
**Goal**: Establish the zero-dependency CLI architecture with persistent storage for injection tracking
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03
**Success Criteria** (what must be TRUE):
  1. User can run `ricochet --help` and see available commands
  2. User can run `ricochet --version` and see version info
  3. Tool creates SQLite database on first run without external dependencies
  4. Database persists injection records across sessions
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — CLI skeleton with argparse subcommand structure
- [ ] 01-02-PLAN.md — SQLite persistence layer for injection/callback tracking

### Phase 2: HTTP Callback Server
**Goal**: Users can run a local HTTP callback server and track which injections triggered callbacks
**Depends on**: Phase 1
**Requirements**: CALL-02, CALL-03
**Success Criteria** (what must be TRUE):
  1. User can start HTTP callback server with `ricochet listen --http`
  2. Each injection gets a unique correlation ID in the callback URL
  3. When callback fires, tool logs which correlation ID was triggered
  4. User can query which injections have received callbacks
**Plans**: TBD

Plans:
- [ ] 02-01: Correlation ID generation and storage
- [ ] 02-02: HTTP callback server implementation

### Phase 3: DNS & External Callbacks
**Goal**: Users can detect callbacks through DNS (bypasses firewalls) and use Interactsh for real-world testing
**Depends on**: Phase 2
**Requirements**: CALL-01, CALL-04
**Success Criteria** (what must be TRUE):
  1. User can start DNS callback server with `ricochet listen --dns`
  2. DNS queries to correlation subdomains are captured and logged
  3. User can configure Interactsh as callback target instead of local server
  4. Interactsh callbacks are correlated with injections
**Plans**: TBD

Plans:
- [ ] 03-01: DNS callback server implementation
- [ ] 03-02: Interactsh client integration

### Phase 4: Injection Engine
**Goal**: Users can inject payloads into targets via CLI arguments or Burp request files
**Depends on**: Phase 3
**Requirements**: INJ-01, INJ-02, INJ-05, CORE-04, CORE-05
**Success Criteria** (what must be TRUE):
  1. User can inject into specific URL/parameter via `ricochet inject -u URL -p param`
  2. User can provide Burp-format request file via `ricochet inject -r request.txt`
  3. Tool injects into all input vectors (query params, headers, body fields)
  4. User can configure request timeouts
  5. Tool respects rate limiting to avoid target bans
**Plans**: TBD

Plans:
- [ ] 04-01: HTTP client with timeout and rate limiting
- [ ] 04-02: Burp request file parser
- [ ] 04-03: Multi-vector injection logic

### Phase 5: Crawler & Payloads
**Goal**: Users can auto-discover injection points and use custom payload files
**Depends on**: Phase 4
**Requirements**: INJ-03, INJ-04
**Success Criteria** (what must be TRUE):
  1. User can crawl target with `ricochet crawl -u URL`
  2. Crawler discovers forms, URL parameters, and other injection points
  3. User can provide custom payload file with `ricochet inject --payloads payloads.txt`
  4. Custom payloads are injected with correlation IDs appended
**Plans**: TBD

Plans:
- [ ] 05-01: Target crawler for injection point discovery
- [ ] 05-02: Custom payload file loading

### Phase 6: Vulnerability Payloads
**Goal**: Tool generates context-appropriate payloads for XSS, SQLi, and SSTI detection
**Depends on**: Phase 5
**Requirements**: VULN-01, VULN-02, VULN-03, VULN-04
**Success Criteria** (what must be TRUE):
  1. Tool generates XSS payloads that callback when executed in browser context
  2. Tool generates SQLi payloads that callback via out-of-band channels
  3. Tool generates SSTI payloads that callback when template engine processes them
  4. Polyglot payloads work across multiple contexts without modification
  5. Each payload type includes correlation ID for tracking
**Plans**: TBD

Plans:
- [ ] 06-01: XSS payload generator with callback embedding
- [ ] 06-02: SQLi OOB payload generator
- [ ] 06-03: SSTI payload generator
- [ ] 06-04: Polyglot payload generation

### Phase 7: Correlation & Output
**Goal**: Tool correlates callbacks with injections and outputs findings in multiple formats
**Depends on**: Phase 6
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04
**Success Criteria** (what must be TRUE):
  1. When callback fires, tool identifies the exact injection point that triggered it
  2. User can get findings in JSON format with `-o json`
  3. User can get human-readable output with `-o text`
  4. User can enable verbose/debug mode to see payloads and responses
  5. User can route traffic through HTTP proxy with `--proxy`
**Plans**: TBD

Plans:
- [ ] 07-01: Callback-injection correlation engine
- [ ] 07-02: Output formatters (JSON, text, verbose)
- [ ] 07-03: Proxy support integration

### Phase 8: Triggers & Reporting
**Goal**: Tool helps trigger payload execution and generates bug bounty reports
**Depends on**: Phase 7
**Requirements**: TRIG-01, TRIG-02, TRIG-03, OUT-05, CALL-05
**Success Criteria** (what must be TRUE):
  1. User can run passive mode that injects and polls for callbacks
  2. User can run active mode that attempts to trigger execution contexts
  3. Tool suggests likely trigger points based on injection context
  4. When XSS fires, callback captures DOM, cookies, URL, user-agent
  5. User can generate bug bounty report with PoC steps
**Plans**: TBD

Plans:
- [ ] 08-01: Passive polling mode
- [ ] 08-02: Active trigger engine
- [ ] 08-03: Trigger suggestions logic
- [ ] 08-04: XSS metadata capture
- [ ] 08-05: Bug bounty report generator

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/2 | In progress | - |
| 2. HTTP Callback Server | 0/2 | Not started | - |
| 3. DNS & External Callbacks | 0/2 | Not started | - |
| 4. Injection Engine | 0/3 | Not started | - |
| 5. Crawler & Payloads | 0/2 | Not started | - |
| 6. Vulnerability Payloads | 0/4 | Not started | - |
| 7. Correlation & Output | 0/3 | Not started | - |
| 8. Triggers & Reporting | 0/5 | Not started | - |
