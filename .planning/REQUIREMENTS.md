# Requirements: Ricochet

**Defined:** 2026-01-29
**Core Value:** Detect vulnerabilities that execute in a different context than where they were injected

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Callback Infrastructure

- [ ] **CALL-01**: Tool integrates with Interactsh for out-of-band callback detection
- [ ] **CALL-02**: Tool generates unique correlation IDs linking injections to callbacks
- [ ] **CALL-03**: Tool can run its own HTTP callback server for local testing
- [ ] **CALL-04**: Tool can run its own DNS callback server for firewall-bypassing detection
- [ ] **CALL-05**: When XSS fires, tool captures metadata (DOM snapshot, cookies, URL, user-agent)

### Vulnerability Detection

- [ ] **VULN-01**: Tool detects blind/stored XSS via callback confirmation
- [ ] **VULN-02**: Tool detects second-order SQL injection via callback confirmation
- [ ] **VULN-03**: Tool detects SSTI (Server-Side Template Injection) via callback confirmation
- [ ] **VULN-04**: Tool generates context-appropriate polyglot payloads for each vulnerability type

### Injection Modes

- [ ] **INJ-01**: Tool accepts HTTP request files (Burp format) as input
- [ ] **INJ-02**: Tool accepts targeted URL + parameter specification via CLI
- [ ] **INJ-03**: Tool can crawl target to discover injection points automatically
- [ ] **INJ-04**: Tool supports loading custom payloads from file
- [ ] **INJ-05**: Tool injects payloads into all identified input vectors (params, headers, body)

### Trigger Mechanisms

- [ ] **TRIG-01**: Tool supports passive mode — inject and poll for callbacks
- [ ] **TRIG-02**: Tool supports active mode — attempt to trigger execution via common endpoints
- [ ] **TRIG-03**: Tool provides suggestions for likely trigger points based on injection context

### Output & Reporting

- [ ] **OUT-01**: Tool outputs findings in JSON format for automation
- [ ] **OUT-02**: Tool outputs findings in human-readable plain text
- [ ] **OUT-03**: Tool supports verbose/debug modes showing payloads and responses
- [ ] **OUT-04**: Tool supports routing traffic through HTTP proxy (Burp integration)
- [ ] **OUT-05**: Tool generates bug bounty ready reports with PoC steps

### Core Infrastructure

- [x] **CORE-01**: Tool is a CLI application with standard Unix conventions
- [x] **CORE-02**: Tool has zero external dependencies (Python stdlib only)
- [x] **CORE-03**: Tool persists injection state to SQLite for correlation across sessions
- [ ] **CORE-04**: Tool supports configurable timeouts for requests and callback polling
- [ ] **CORE-05**: Tool implements rate limiting to avoid bans

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Additional Vulnerability Types

- **VULN-05**: Tool detects command injection via callback confirmation
- **VULN-06**: Tool detects SSRF via callback confirmation

### Advanced Features

- **ADV-01**: Tool performs context detection (HTML/JS/SQL) for smarter payload selection
- **ADV-02**: Tool captures full HTTP response metadata on callback fire
- **ADV-03**: Tool supports session management with cookie persistence

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| GUI interface | Bug bounty hunters live in terminals. CLI-first. |
| Exploitation/post-exploitation | Detection tool, not exploitation framework. Pipe findings to sqlmap/commix. |
| Full web application scanner | Scope creep. Focus on second-order detection niche. |
| Cloud-hosted SaaS | Requires infrastructure, billing, compliance. Self-contained CLI. |
| Browser automation for triggers | Slow, resource-intensive, flaky. HTTP-based triggers first. |
| Machine learning detection | Adds complexity, creates black-box behavior. Pattern-based detection. |
| Asset discovery | subfinder, amass already excel at this. Accept URLs as input. |
| WAF evasion as primary feature | Infinite cat-and-mouse. Support custom payloads instead. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CALL-01 | Phase 3 | Pending |
| CALL-02 | Phase 2 | Pending |
| CALL-03 | Phase 2 | Pending |
| CALL-04 | Phase 3 | Pending |
| CALL-05 | Phase 8 | Pending |
| VULN-01 | Phase 6 | Pending |
| VULN-02 | Phase 6 | Pending |
| VULN-03 | Phase 6 | Pending |
| VULN-04 | Phase 6 | Pending |
| INJ-01 | Phase 4 | Pending |
| INJ-02 | Phase 4 | Pending |
| INJ-03 | Phase 5 | Pending |
| INJ-04 | Phase 5 | Pending |
| INJ-05 | Phase 4 | Pending |
| TRIG-01 | Phase 8 | Pending |
| TRIG-02 | Phase 8 | Pending |
| TRIG-03 | Phase 8 | Pending |
| OUT-01 | Phase 7 | Pending |
| OUT-02 | Phase 7 | Pending |
| OUT-03 | Phase 7 | Pending |
| OUT-04 | Phase 7 | Pending |
| OUT-05 | Phase 8 | Pending |
| CORE-01 | Phase 1 | Complete |
| CORE-02 | Phase 1 | Complete |
| CORE-03 | Phase 1 | Complete |
| CORE-04 | Phase 4 | Pending |
| CORE-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-01-29*
*Last updated: 2026-01-29 after roadmap creation*
