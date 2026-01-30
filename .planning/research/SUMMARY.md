# Project Research Summary

**Project:** Ricochet - Second-Order Vulnerability Detection CLI Tool
**Domain:** Security Testing / OAST-based Scanner
**Researched:** 2026-01-29
**Confidence:** HIGH

## Executive Summary

Ricochet is an Out-of-Band Application Security Testing (OAST) tool designed to detect second-order and blind vulnerabilities (XSS, SQLi, SSTI, Command Injection) through callback-based detection. The research reveals that this domain is well-established with proven patterns from Burp Collaborator, Interactsh, and XSS Hunter, and critically, it's entirely buildable with Python's standard library alone.

The recommended approach centers on correlation-first architecture: every payload embeds a unique correlation ID that links callbacks back to specific injection points. The tool must handle asynchronous, unpredictable callback timing (seconds to weeks) and support multiple callback channels (DNS, HTTP) for reliability. Threading with queue-based coordination is sufficient for concurrency; asyncio adds complexity without benefit given the stdlib-only constraint.

The primary risk is correlation failure - receiving callbacks but being unable to trace them to injection points renders the tool useless. Mitigation requires cryptographically secure correlation IDs embedded in payloads, persistent state storage (SQLite), and flexible correlation time windows. Secondary risks include callback server blocking (mitigated via DNS fallback), authentication state loss during crawling (requires proactive session refresh), and context-blind payloads (needs context detection). These are all addressable with careful architecture from day one.

## Key Findings

### Recommended Stack

Python's standard library provides complete coverage for this domain. The stdlib-only constraint is not just feasible - it's actually elegant. Key modules map cleanly to architecture needs: `argparse` for CLI, `urllib.request` for HTTP injection, `html.parser.HTMLParser` for form extraction, `http.server.ThreadingHTTPServer` for callbacks, `struct` for DNS packet parsing, `concurrent.futures.ThreadPoolExecutor` for parallelism, and `sqlite3` for persistence.

**Core technologies:**
- **Python 3.9+** (3.11+ recommended): Base runtime - no external dependencies needed
- **urllib.request + urllib.parse**: HTTP client for payload injection - handles cookies, headers, POST/GET
- **http.server.ThreadingHTTPServer**: HTTP callback server - built-in threading for concurrent callbacks
- **socketserver.ThreadingUDPServer + struct**: DNS callback server - parse DNS wire format for callbacks
- **html.parser.HTMLParser**: Form/input extraction - event-driven parsing for crawling
- **concurrent.futures.ThreadPoolExecutor**: Parallel injection - I/O-bound workload benefits from threading
- **sqlite3**: State persistence - ACID compliance for injection-callback correlation
- **argparse**: CLI interface - subcommand support for inject/listen/correlate workflow

**Critical version requirements:**
- Minimum Python 3.9 for modern type hints and stdlib improvements
- `ThreadingHTTPServer` requires Python 3.7+ (built-in threaded HTTP server)
- DNS server requires root privileges for port 53 (or use capabilities/high port)

### Expected Features

Research shows a clear gap in the market: no single open-source CLI tool unifies second-order detection across XSS, SQLi, SSTI, and Command Injection. Hunters currently use separate tools (Dalfox for XSS, sqlmap for SQLi, tplmap for SSTI, commix for command injection) or expensive Burp Suite Pro.

**Must have (table stakes):**
- **Out-of-band callback detection** (DNS + HTTP minimum) - core mechanism, without this it's just a payload injector
- **Interactsh integration** - de facto standard, Nuclei/ZAP use it, bug bounty hunters expect it
- **Multiple vulnerability types** (XSS, SQLi, SSTI, Command Injection) - unified workflow is the differentiator
- **Request file input** (Burp format) - dominant workflow, hunters export from Burp to specialized tools
- **CLI interface with automation support** - pipeable, machine-parseable output for chaining tools
- **Payload customization** - every target needs different payloads/encoding for WAF bypass
- **Output formats** (JSON, plain text) - JSON for automation, text for review
- **Verbose/debug mode** - essential for troubleshooting when things don't work
- **Proxy support** - route through Burp/Caido to inspect traffic

**Should have (competitive):**
- **Automatic injection-to-trigger correlation** - track which injection caused which callback, critical for reporting
- **Built-in callback server** - zero-config alternative to Interactsh for simple cases
- **Trigger point suggestions** - suggest where second-order payloads might execute (admin panels, logs, exports)
- **Session management** - persist cookies/tokens across injection and trigger phases
- **Report generation** - auto-generate bug bounty report templates with PoC steps
- **Context-aware payloads** - detect injection context (HTML vs JSON vs SQL) and adapt payloads

**Defer (v2+):**
- **Auto-crawl mode** - complex feature, hunters can use external tools initially (katana, gospider)
- **Payload fire metadata capture** - XSS Hunter-style DOM snapshots, valuable but not essential
- **GUI interface** - CLI-first, GUI only if clear demand emerges
- **Browser automation for triggers** - slow and flaky, HTTP-based triggering sufficient initially

### Architecture Approach

Ricochet follows OAST architecture patterns: payloads fire asynchronously and unpredictably at time T+N (seconds to weeks) after injection at time T. The architecture must decouple injection, callback reception, and correlation into independent phases that communicate through persistent storage.

**Major components:**
1. **CLI Interface** - orchestrates workflow, parses commands (inject/listen/trigger/correlate/report)
2. **Injection Engine** - crawls target, identifies injection points, generates unique payloads, stores injection metadata
3. **Payload Generator** - creates context-aware payloads with embedded correlation IDs, supports XSS/SQLi/SSTI/CMDi
4. **Callback Server** (HTTP + DNS) - runs continuously in background thread, receives callbacks, extracts correlation IDs
5. **Injection Store** (SQLite) - persists injection records, callback records, correlation state
6. **Trigger Engine** - optionally requests pages that might execute stored payloads (admin panels, exports)
7. **Correlation Engine** - matches callback IDs to injection records, computes vulnerability findings
8. **Report Generator** - formats findings as JSON/text/markdown for bug bounty submissions

**Threading model:** Main thread runs injection engine sequentially. Callback server runs in daemon thread using `ThreadingHTTPServer` and `ThreadingUDPServer`. Communication via `queue.Queue`. This is simpler than asyncio and sufficient for I/O-bound workload.

**Correlation ID design:** `{random_prefix}.{injection_hash}.{callback_domain}` embedded in every payload. Enables cryptographically secure linking of callbacks to injections. Extracted from subdomain or URL path on callback.

### Critical Pitfalls

Research identified several domain-specific failure modes that must be addressed in architecture:

1. **Callback-injection correlation failure** - callbacks arrive but can't be traced to specific injections. Prevention: embed correlation IDs in payload structure (not just subdomain), use cryptographic nonces, maintain state mapping with configurable time windows (24h default, extendable to 7d). Address in Phase 1 (foundational).

2. **Callback server reliability and blocking** - public OAST servers get blocked by firewalls, self-hosted servers have DNS config issues. Prevention: support multiple providers with fallback (Interactsh -> self-hosted -> DNS-only), DNS is minimum viable (most environments allow DNS). Implement health monitoring. Address in Phase 1-2.

3. **Session/authentication state loss during crawling** - tokens expire mid-scan, payloads injected into login pages instead of authenticated endpoints. Prevention: proactive token refresh, detect 401/403 and re-auth, support multiple auth methods. Address in Phase 2 (crawler).

4. **Context-blind payload generation** - wrong payloads for execution context (JavaScript payload in SQL query). Prevention: context detection based on Content-Type/response structure, context-specific templates, proper encoding chains. Address in Phase 3 (payloads).

5. **Rate limiting and target overload** - aggressive scanning triggers WAF blocks or bans. Prevention: conservative defaults (2-5 RPS), automatic backoff on 429/503, respect Retry-After headers, WAF detection. Address in Phase 2 (crawler).

## Implications for Roadmap

Based on research, the architecture has clear dependency chains that dictate build order. The roadmap should follow a foundation-first approach where each phase delivers working functionality while building toward the complete system.

### Phase 1: Foundation & Callback Infrastructure
**Rationale:** Correlation is the linchpin - without it, the tool cannot confirm second-order findings. The injection store and callback servers must exist before any payload injection happens. This phase establishes the core mechanism that makes second-order detection possible.

**Delivers:**
- SQLite-based injection store with schema for injections/callbacks/correlations
- Correlation ID generation utilities (cryptographically secure)
- HTTP callback server (ThreadingHTTPServer) running in background thread
- DNS callback server (optional, requires root/capabilities)
- Basic queue-based coordination between main thread and callback threads

**Addresses:**
- Correlation failure pitfall (P1) - build correlation system first
- Callback server reliability (P2) - multi-channel support from start

**Avoids:** Building injection logic before callback infrastructure exists (waste of effort)

**Research flag:** Standard patterns - HTTP/DNS server implementation is well-documented in stdlib docs

### Phase 2: Injection Engine & Crawler
**Rationale:** With callback infrastructure ready, we can inject payloads and receive callbacks. The injection engine needs form extraction, parameter identification, and HTTP request capabilities. Session management and rate limiting are critical from day one to avoid auth loss and WAF blocks.

**Delivers:**
- HTML form parser using `html.parser.HTMLParser`
- HTTP request wrapper with cookie jar and session persistence
- Basic crawler for link/form discovery
- Request file input (Burp format parsing)
- Rate limiting with configurable delays and backoff
- Scope enforcement (whitelist-based, prevent out-of-scope testing)
- Session health monitoring and refresh logic

**Addresses:**
- Auth state loss (P3) - proactive session refresh
- Rate limiting (P7) - built into request layer
- Scope creep (P8) - strict whitelist enforcement

**Uses:**
- `urllib.request` for HTTP client
- `http.cookiejar` for session persistence
- `html.parser` for form extraction

**Research flag:** Standard patterns - form parsing and HTTP client usage well-documented

### Phase 3: Payload Generation (Multi-Vuln Support)
**Rationale:** Start with XSS + SQLi (most common second-order vulns in bug bounty), then add SSTI + CMDi. Each vulnerability type requires different payload templates and detection logic. Context detection improves accuracy by matching payloads to execution context.

**Delivers:**
- Payload templates for XSS (HTML, JavaScript, attribute contexts)
- Payload templates for SQLi (stacked queries, time-based, OOB)
- Payload templates for SSTI (Jinja2, ERB, Twig)
- Payload templates for Command Injection (curl, wget, nslookup)
- Context detection (HTML vs JSON vs SQL based on Content-Type)
- Custom payload file support
- Correlation ID embedding in all payload types

**Addresses:**
- Context-blind payloads (P4) - context detection drives selection
- Must-have feature: multiple vulnerability types
- Must-have feature: payload customization

**Implements:** Payload Generator component with context-aware templates

**Research flag:** Skip research for XSS/SQLi (standard patterns). May need research for SSTI (template-specific escaping).

### Phase 4: Correlation & Basic Reporting
**Rationale:** Connect injections to callbacks and produce actionable findings. This completes the minimal viable workflow: inject -> callback -> correlate -> report. Noise filtering from day one prevents false positive fatigue.

**Delivers:**
- Correlation engine matching callback IDs to injection records
- Confidence scoring (DNS-only = LOW, HTTP with correlation = MEDIUM, full execution proof = HIGH)
- Noise filtering (user-agent analysis, timing patterns, deduplication)
- JSON output format (automation-friendly)
- Plain text output format (human-readable)
- CLI subcommands: correlate, report

**Addresses:**
- Callback noise and false positives (P5) - confidence scoring and filtering
- Must-have feature: output formats
- Should-have feature: automatic correlation

**Implements:** Correlation Engine and Report Generator components

**Research flag:** Standard patterns - SQL queries and JSON formatting well-understood

### Phase 5: Trigger Mechanisms & Advanced Features
**Rationale:** Active triggering speeds up detection by requesting pages that execute stored payloads (admin panels, exports, logs). This phase also adds Interactsh integration as alternative to built-in server.

**Delivers:**
- Trigger engine that requests common execution contexts
- Trigger point suggestions based on injection location
- Interactsh API integration (use external OAST service)
- Long-running callback polling (configurable duration)
- Markdown report generation for bug bounty submissions
- Session replay for complex auth flows

**Addresses:**
- Execution context triggering (P6) - active trigger + long polling
- Must-have feature: Interactsh integration
- Should-have feature: trigger point suggestions
- Should-have feature: report generation

**Implements:** Trigger Engine component

**Research flag:** Needs research - Interactsh API integration requires studying their docs/SDK

### Phase 6: Polish & Enhancements
**Rationale:** Quality-of-life improvements that make the tool production-ready for bug bounty hunters.

**Delivers:**
- Scan state persistence and resume functionality
- Verbose logging with debug mode
- Scan progress indicators
- Performance optimizations (ThreadPoolExecutor for parallel injection)
- Comprehensive error handling and user-friendly messages
- Documentation and usage examples

**Addresses:**
- Poor scan state management (P9)
- Inadequate logging (P10)
- Must-have features: verbose/debug mode, timeout controls

**Research flag:** Standard patterns - well-known CLI UX practices

### Phase Ordering Rationale

- **Foundation first (Phase 1):** Callback infrastructure must exist before injection starts. Building injection without correlation capability wastes effort.
- **Injection before correlation (Phases 2-3 before 4):** Need injections and callbacks to test correlation logic.
- **XSS + SQLi before SSTI + CMDi (Phase 3):** Most common vulns in bug bounty, deliver value sooner.
- **Basic reporting before advanced features (Phase 4 before 5):** Complete the MVP workflow before adding trigger mechanisms.
- **Polish last (Phase 6):** Core functionality must work before optimizing UX.

This ordering follows dependency chains discovered in architecture research and avoids the major pitfalls identified in domain research.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 5 (Interactsh Integration):** API integration requires studying their REST/WebSocket API, authentication, and rate limits. Documentation available but needs detailed review.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Callback Infrastructure):** HTTP/DNS server patterns well-documented in Python stdlib docs
- **Phase 2 (Injection Engine):** urllib.request and html.parser have extensive documentation
- **Phase 3 (XSS/SQLi Payloads):** Standard patterns from OWASP, PortSwigger resources
- **Phase 4 (Correlation):** SQLite queries and JSON formatting are well-understood
- **Phase 6 (Polish):** Standard CLI UX patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All modules verified in Python 3.9+ stdlib documentation. Working code examples provided in STACK.md. |
| Features | MEDIUM | Feature landscape synthesized from multiple tools (Burp, Interactsh, XSS Hunter, Dalfox, sqlmap). Market gap validated but user preferences inferred from tool popularity. |
| Architecture | HIGH | OAST architecture patterns verified against Burp Collaborator, Interactsh, XSS Hunter implementations. Correlation-first design is proven in production tools. |
| Pitfalls | MEDIUM | Critical pitfalls sourced from PortSwigger research and OWASP. Moderate/minor pitfalls inferred from community discussions and tool issue trackers. |

**Overall confidence:** HIGH

The stdlib-only constraint significantly reduces uncertainty - no dependency compatibility issues, version conflicts, or supply chain risks. The OAST architecture is battle-tested in multiple production tools. The main uncertainty is feature prioritization (which features hunters value most), but the MVP scope (XSS + SQLi + Interactsh) is clearly validated.

### Gaps to Address

**Interactsh API details:** FEATURES.md identifies Interactsh integration as must-have, but API specifics need research during Phase 5 planning. Check for authentication requirements, rate limits, response formats, WebSocket vs polling.

**SSTI payload escaping:** Template engines (Jinja2, ERB, Twig, etc.) have different escaping rules. Phase 3 may need deeper research into template-specific bypass techniques. Initial implementation can use generic SSTI payloads, refine later.

**Trigger point heuristics:** Suggesting where second-order payloads execute requires domain knowledge (contact form -> admin ticket view, user profile -> admin user list). Build heuristics iteratively based on testing, not comprehensive upfront research.

**WAF detection patterns:** Identifying WAF blocking is complex (many WAF vendors, different behaviors). Start simple (detect 403/429 patterns), enhance based on field testing.

**Long-running scan UX:** Second-order vulns may trigger days later. How to notify users of delayed callbacks? Consider: persistent scan IDs, callback webhook notifications, email alerts. Address during Phase 4-5 planning.

## Sources

### Primary (HIGH confidence)
- Python stdlib documentation (argparse, urllib.request, http.server, socketserver, html.parser, concurrent.futures, sqlite3, struct) - verified module capabilities and code examples
- PortSwigger OAST Overview and Burp Collaborator docs - OAST architecture patterns
- ProjectDiscovery Interactsh documentation - callback service architecture
- OWASP Session Management and Blind SQL Injection - security testing patterns

### Secondary (MEDIUM confidence)
- XSS Hunter GitHub (mandatoryprogrammer/xsshunter-express) - blind XSS correlation implementation
- Bugcrowd Guide to Blind XSS - second-order detection techniques
- Dalfox, sqlmap, tplmap, commix GitHub repos - feature comparison and workflow analysis
- Nuclei + Interactsh integration blog - OAST integration patterns
- NetSPI Second-Order SQLi with DNS Egress - DNS callback techniques

### Tertiary (LOW confidence)
- GitHub issue discussions on Nuclei correlation - community-reported edge cases
- Individual bug bounty writeups - specific bypass techniques (validate before relying)

---
*Research completed: 2026-01-29*
*Ready for roadmap: yes*
