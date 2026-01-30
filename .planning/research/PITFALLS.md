# Domain Pitfalls: Second-Order Vulnerability Detection

**Domain:** CLI tool for detecting second-order/blind vulnerabilities (OAST-based)
**Researched:** 2026-01-29
**Confidence:** MEDIUM (verified against multiple sources including PortSwigger, ProjectDiscovery, OWASP)

---

## Critical Pitfalls

Mistakes that cause complete tool failure, rewrites, or make the tool unusable in real-world scenarios.

### Pitfall 1: Callback-Injection Correlation Failure

**What goes wrong:** The scanner detects callbacks but cannot reliably trace them back to the specific payload/injection point that caused them. Users get alerts like "something triggered a callback" but no actionable information about what vulnerability exists or where.

**Why it happens:**
- Correlation IDs get truncated by the target application
- Multiple payloads fire simultaneously, creating ambiguous callback attribution
- Async operations in the target scramble timing-based correlation
- DNS resolution caching causes callbacks to appear minutes/hours after injection

**Consequences:**
- False positives flood the results (noise without signal)
- Users cannot reproduce or verify vulnerabilities
- Tool becomes useless for actual pentesting/bug bounty work

**Prevention:**
- Embed correlation IDs directly in payload structure, not just in subdomain
- Use cryptographic binding: each payload contains a unique nonce that appears in both the injection and the callback
- Maintain state mapping: `injection_id -> (target_url, parameter, payload_type, timestamp)`
- Support configurable correlation windows (default 24h, extendable to 7d for slow async systems)

**Detection (warning signs):**
- During testing: callbacks arrive but `correlation_id` is empty/malformed
- User reports: "I got a callback but don't know which endpoint triggered it"
- Metric: >30% of callbacks have degraded correlation confidence

**Phase to address:** Phase 1 (Core Architecture) - This is foundational. Build correlation system before any payload generation.

**Sources:**
- [PortSwigger Research on Async Vulnerabilities](https://portswigger.net/research/hunting-asynchronous-vulnerabilities)
- [Nuclei Interactsh Correlation Issues](https://github.com/projectdiscovery/nuclei/issues/1844)

---

### Pitfall 2: Callback Server Reliability and Blocking

**What goes wrong:** Public callback servers (interact.sh, oastify.com) get blocked by target firewalls, rate-limited, or experience downtime. Self-hosted servers have DNS configuration issues or become a single point of failure.

**Why it happens:**
- Security teams block known OAST domains (interact.sh is commonly flagged)
- Target environments restrict outbound DNS/HTTP
- Public servers have usage limits and rotating availability
- Self-hosted servers require correct wildcard DNS, TLS, and network configuration

**Consequences:**
- Vulnerabilities exist but no callback is received (false negatives)
- Scanner reports "clean" when target is actually vulnerable
- Unreliable results destroy user trust in the tool

**Prevention:**
- Support multiple callback providers with automatic fallback (interact.sh -> self-hosted -> DNS-only)
- Provide DNS-based detection as minimum viable callback (most environments allow DNS)
- For self-hosted: provide clear setup documentation, health-check endpoint
- Implement callback server health monitoring before/during scans
- Consider support for custom domains to evade blocking

**Detection (warning signs):**
- Zero callbacks on a target that should have basic vulnerabilities
- Callback server health checks fail but scan continues
- Timeouts increase dramatically for certain target ranges

**Phase to address:** Phase 1-2 (Core Architecture + Callback Infrastructure)

**Sources:**
- [Interactsh GitHub - Default server rotation](https://github.com/projectdiscovery/interactsh)
- [Free Burp Collaborator Alternatives](https://beauknows.tech/posts/collaborator-alternatives/)

---

### Pitfall 3: Session/Authentication State Loss During Crawling

**What goes wrong:** The crawler starts authenticated, but sessions expire mid-scan. Payloads get injected into login pages or error pages instead of the actual authenticated attack surface. Critical endpoints never get tested.

**Why it happens:**
- Access tokens expire (often 15-30 minutes)
- Refresh token logic not implemented
- Session cookies invalidated by concurrent requests
- CSRF tokens become stale
- Target has aggressive session timeout policies

**Consequences:**
- Incomplete attack surface coverage
- Payloads wasted on unauthenticated endpoints
- User thinks scan is complete when critical areas untested
- Blind XSS payloads never reach admin panels because auth failed

**Prevention:**
- Implement proactive token refresh (refresh 1 minute before expiry)
- Support multiple authentication methods: cookie, header, OAuth flow
- Detect authentication loss (401/403 responses, redirect to login) and pause/re-auth
- Provide session health indicator in scan status
- Support session recording/replay for complex auth flows
- Allow users to provide refresh token endpoint configuration

**Detection (warning signs):**
- Sudden spike in 401/403 responses mid-scan
- Crawled URLs shift from `/api/admin/*` to `/login`
- Scan discovers far fewer endpoints than expected

**Phase to address:** Phase 2 (Crawler Development) - Auth handling must be robust before extensive payload injection.

**Sources:**
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [Auth.js Refresh Token Rotation](https://authjs.dev/guides/refresh-token-rotation)

---

### Pitfall 4: Context-Blind Payload Generation

**What goes wrong:** Payloads are generated without understanding the execution context. A JavaScript payload is injected into a SQL query. An HTML payload is injected into a JSON API. Payloads fail to execute because they don't match the rendering/execution context.

**Why it happens:**
- Generic payload lists applied uniformly
- No context detection (HTML vs JSON vs SQL vs shell)
- Improper encoding for the target context
- Polyglot payloads are complex and often break more than they exploit

**Consequences:**
- Low true positive rate despite high injection count
- Real vulnerabilities missed because payload didn't match context
- Target application errors instead of executing payload
- WAFs easily detect non-contextual payloads

**Prevention:**
- Implement context detection based on Content-Type, response structure
- Context-specific payload templates: HTML context, JavaScript context, SQL context, shell context
- Proper encoding chains: URL-encode for query params, HTML-entity for HTML, JSON-escape for JSON
- Test payload validity: does this payload survive the injection path intact?
- Support custom payload templates for unusual contexts

**Detection (warning signs):**
- High injection count but zero callbacks
- Target returns many 400/500 errors during injection
- Payloads visible in responses but clearly malformed/escaped

**Phase to address:** Phase 3 (Payload Generation) - Context detection should inform payload selection.

**Sources:**
- [PortSwigger: Obfuscating Attacks Using Encodings](https://portswigger.net/web-security/essential-skills/obfuscating-attacks-using-encodings)
- [PayloadsAllTheThings SQLi Reference](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/README.md)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or reduced effectiveness but are recoverable.

### Pitfall 5: Callback Noise and False Positives

**What goes wrong:** The callback server receives legitimate traffic, scanner pings, health checks, or other noise that gets reported as vulnerabilities. Users waste hours investigating non-exploitable "findings."

**Why it happens:**
- Callback URLs get indexed by search engines or scraped
- Automated systems (WAFs, security scanners) make requests to detected URLs
- DNS prefetching triggers callback without actual vulnerability
- Correlation window too wide, matching unrelated callbacks

**Prevention:**
- Require minimum callback threshold (e.g., DNS + HTTP, not just DNS)
- Implement payload verification: callback must contain data that proves code execution
- Score callbacks by confidence: DNS-only = LOW, HTTP with correlation = MEDIUM, full payload execution = HIGH
- Filter obvious noise: user-agent analysis, timing patterns, source IP reputation
- Deduplicate callbacks from same source

**Detection (warning signs):**
- Callbacks from IPs not in target scope
- Callback data doesn't match expected payload structure
- Same "vulnerability" reported across many unrelated targets

**Phase to address:** Phase 4 (Callback Processing) - Implement noise filtering from the start.

**Sources:**
- [Invicti: Reduce DAST False Positives](https://www.invicti.com/blog/web-security/reduce-dast-false-positives)

---

### Pitfall 6: Execution Context Triggering Failures

**What goes wrong:** Payloads are injected successfully and stored, but never execute because the execution context is never triggered. Blind XSS sits in admin logs that nobody views. Second-order SQLi waits in a cron job that runs monthly.

**Why it happens:**
- Admin panels require manual access (nobody viewing injected data)
- Background jobs run on schedules outside scan window
- Execution depends on specific user actions
- Email templates only render when emails are sent

**Consequences:**
- Real vulnerabilities exist but scanner reports clean
- User confidence in tool diminishes
- Critical blindspots in coverage

**Prevention:**
- Document what the tool can and cannot trigger (honest capability reporting)
- Provide "trigger hints" for common contexts (e.g., "Try accessing /admin/logs to trigger")
- Support long-running callback windows (days/weeks) for slow-triggering vulns
- Consider active triggering where safe: request admin endpoints, trigger background jobs via known APIs
- Track "pending" injections that haven't called back yet

**Detection (warning signs):**
- High injection success rate but low callback rate
- Callbacks cluster around specific trigger events
- Manual testing finds vulns that automated scan missed

**Phase to address:** Phase 5 (Trigger Mechanisms) - Active triggering is a differentiator but needs careful implementation.

---

### Pitfall 7: Rate Limiting and Target Overload

**What goes wrong:** Aggressive scanning triggers WAF blocks, rate limiting, or service degradation. The target's security team notices the scan and blocks the source IP. In bug bounty, this can get the hunter banned.

**Why it happens:**
- Default scan settings too aggressive
- No backoff on rate limit responses
- Payload injection creates high request volume
- Concurrent requests overwhelm target

**Consequences:**
- Scan blocked mid-execution, incomplete results
- IP banned, losing access to target
- Bug bounty account flagged/suspended
- Potential legal issues if service disruption

**Prevention:**
- Conservative defaults (2-5 RPS), user must explicitly increase
- Automatic backoff on 429/503 responses
- Respect Retry-After headers
- Provide "stealth mode" with randomized delays
- Configurable request rate per target
- WAF detection and adaptive throttling

**Detection (warning signs):**
- Increasing 429/503 responses during scan
- Sudden timeout/connection refused patterns
- Target endpoints return different responses (WAF blocks)

**Phase to address:** Phase 2 (Crawler) - Rate limiting must be built into request layer.

**Sources:**
- [Intigriti: Aggressive Scanning in Bug Bounty](https://blog.intigriti.com/hacking-tools/aggressive-scanning-in-bug-bounty-and-how-to-avoid-it)
- [Nuclei at Mass Scale](https://ott3rly.com/using-nuclei-at-mass-scale/)

---

### Pitfall 8: Scope Creep and Out-of-Scope Testing

**What goes wrong:** Crawler follows links to third-party domains, CDNs, or out-of-scope assets. Payloads get injected into systems the user doesn't have permission to test. Legal liability ensues.

**Why it happens:**
- Links lead to external domains
- Shared infrastructure (same IP, different domains)
- User provides broad scope without understanding implications
- Redirects lead outside scope

**Consequences:**
- Testing unauthorized systems (potentially illegal)
- Triggering alerts at third-party security teams
- Bug bounty scope violation and ban
- Legal liability for the user AND potentially the tool maintainer

**Prevention:**
- Strict scope enforcement by default (whitelist, not blacklist)
- Require explicit scope confirmation before scan
- Warn loudly when following redirects outside scope
- Log all requests with scope status for audit
- Support scope formats: domains, IP ranges, URL patterns
- Never auto-expand scope without user confirmation

**Detection (warning signs):**
- Requests to domains not in scope list
- Redirects followed to external domains
- Callbacks from unexpected infrastructure

**Phase to address:** Phase 2 (Crawler) - Scope enforcement is foundational safety feature.

**Sources:**
- [SecureIdeas: Legal Considerations for Pentesting](https://www.secureideas.com/knowledge/what-are-the-ethical-and-legal-considerations-for-penetration-testing)
- [Infosec Institute: Penetration Testing and the Law](https://www.infosecinstitute.com/resources/penetration-testing/penetration-testing-and-the-law/)

---

## Minor Pitfalls

Mistakes that cause annoyance but are easily fixable.

### Pitfall 9: Poor Scan State Management

**What goes wrong:** Scan crashes or user interrupts it. All progress lost. User must restart from zero. No ability to resume.

**Why it happens:**
- State not persisted during scan
- No checkpointing mechanism
- Crash recovery not implemented

**Prevention:**
- Persist scan state to disk/database regularly
- Support pause/resume functionality
- Track which URLs processed, which payloads injected
- On restart, detect and offer to resume previous scan

**Phase to address:** Phase 2 (Crawler) - State management enables long-running scans.

---

### Pitfall 10: Inadequate Logging and Debugging

**What goes wrong:** Something fails but user can't determine why. Support requests are "it doesn't work" with no diagnostic information.

**Why it happens:**
- Insufficient logging at appropriate levels
- Errors swallowed without context
- No debug mode for verbose output

**Prevention:**
- Structured logging with levels (debug, info, warn, error)
- Include context in logs (URL, payload ID, response code)
- Debug mode that shows full request/response
- Export scan report with diagnostic details

**Phase to address:** Phase 1 - Logging framework should be established early.

---

### Pitfall 11: Ignoring Response Analysis Opportunities

**What goes wrong:** Scanner only waits for callbacks, missing vulnerabilities that are detectable in responses. Reflected XSS, error-based SQLi, and time-based detection all ignored.

**Why it happens:**
- Exclusive focus on OOB/callback detection
- Response analysis seen as separate tool's job
- Complexity of parsing diverse responses

**Consequences:**
- Missed vulnerabilities that don't require callbacks
- Tool seen as less capable than competitors
- User must run multiple tools for complete coverage

**Prevention:**
- Implement basic response analysis alongside callback detection
- Detect payload reflection in responses
- Time-based detection for blind injections
- Error message analysis for information disclosure
- Mark this as optional/future feature if time-constrained

**Phase to address:** Phase 4 or Later - Nice to have, not core to second-order focus.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Core Architecture | Correlation failure (P1) | Design correlation system first, before any payload logic |
| Callback Infrastructure | Server blocking (P2) | Multi-provider fallback, DNS minimum viable |
| Crawler Development | Auth loss (P3), Scope creep (P8), Rate limits (P7) | Build auth refresh, scope enforcement, rate limiting into request layer |
| Payload Generation | Context-blind payloads (P4) | Context detection drives payload selection |
| Callback Processing | Noise/false positives (P5) | Confidence scoring from day one |
| Trigger Mechanisms | Execution context not triggered (P6) | Document limitations, provide trigger hints |

---

## Domain-Specific Watchlist

These are not "pitfalls" but areas requiring ongoing attention:

### Second-Order Timing Windows

Second-order vulnerabilities may trigger hours, days, or weeks after injection. Design decisions:
- How long do you wait for callbacks before marking scan "complete"?
- How do you notify users of delayed callbacks?
- How do you handle injection-to-callback correlation across long time periods?

### Callback Data Sensitivity

Callbacks may exfiltrate sensitive data (cookies, DOM content, user info). Consider:
- Data handling and storage policies
- Option to filter/redact sensitive data
- Compliance implications (GDPR) if storing captured credentials

### Target-Specific Behaviors

Different targets behave differently:
- SPA frameworks may not trigger payloads in traditional ways
- API-only targets have limited injection surfaces
- Legacy systems may have unusual encoding requirements

---

## Sources

**HIGH Confidence (Official Documentation):**
- [PortSwigger: Hunting Asynchronous Vulnerabilities](https://portswigger.net/research/hunting-asynchronous-vulnerabilities)
- [PortSwigger: Testing for Blind XSS](https://portswigger.net/burp/documentation/desktop/testing-workflow/input-validation/xss/testing-for-blind-xss)
- [OWASP: Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP: Blind SQL Injection](https://owasp.org/www-community/attacks/Blind_SQL_Injection)
- [ProjectDiscovery: Interactsh Documentation](https://docs.projectdiscovery.io/tools/interactsh/running)

**MEDIUM Confidence (Verified Community Sources):**
- [Bugcrowd: Guide to Blind XSS](https://www.bugcrowd.com/blog/the-guide-to-blind-xss-advanced-techniques-for-bug-bounty-hunters-worth-250000/)
- [Intigriti: Hunting Blind XSS](https://www.intigriti.com/researchers/blog/hacking-tools/hunting-for-blind-cross-site-scripting-xss-vulnerabilities-a-complete-guide)
- [NetSPI: Second-Order SQLi with DNS Egress](https://www.netspi.com/blog/technical-blog/web-application-pentesting/second-order-sql-injection-with-stored-procedures-dns-based-egress/)
- [Offensive360: Second-Order SQL Injection Explained](https://offensive360.com/second-order-sql-injection-attack/)

**LOW Confidence (Single Source, Verify Before Relying):**
- Community discussions on Nuclei correlation issues
- Individual bug bounty writeups on specific bypass techniques
