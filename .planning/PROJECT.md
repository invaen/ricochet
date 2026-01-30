# Ricochet

## What This Is

A CLI tool for detecting second-order vulnerabilities — bugs where the injection point and execution point are different. You inject a payload in a user profile field, it fires when an admin views a dashboard. You put malicious data in a header, it executes when a background job processes logs. Ricochet finds these bugs that traditional scanners miss.

## Core Value

Detect vulnerabilities that execute in a different context than where they were injected — the bugs that pay bounties because they're hard to find.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Inject payloads that phone home when executed via callback server
- [ ] Support multiple vulnerability types: XSS, SQLi, SSTI, Command Injection
- [ ] Generate context-aware polyglot payloads that work across execution contexts
- [ ] Track injections and correlate with callbacks to identify vulnerable parameters
- [ ] Multiple injection modes: auto-crawl, targeted endpoint, marked request file
- [ ] Built-in callback listener for local testing
- [ ] Interactsh integration for real-world testing without infrastructure
- [ ] Passive monitoring mode (inject and wait)
- [ ] Active trigger modules (attempt to trigger execution contexts)
- [ ] Guided mode (suggest actions that might trigger execution)

### Out of Scope

- GUI/web interface — CLI only for v1
- Browser extension — future consideration
- Burp Suite integration — may add later but not v1
- Automated exploitation — detection only, not weaponization
- SSRF detection — different attack pattern, consider for v2

## Context

**Problem space:** Second-order vulnerabilities are high-value targets in bug bounty. They bypass WAFs (payload doesn't execute at ingress), reach privileged contexts (admin panels, internal tools), and are missed by automated scanners. Currently, finding them is entirely manual — inject payloads, wait, hope something fires.

**Existing tools:**
- Burp Collaborator does callback detection but no injection automation
- Interactsh provides free callback infrastructure but no scanning logic
- No open source tool combines intelligent injection with callback correlation for second-order detection

**Target users:** Bug bounty hunters, penetration testers, security researchers who want to find the bugs that others miss.

**Technical approach:**
1. **Injection engine** — crawl/parse/inject payloads into all identified inputs
2. **Payload generator** — context-aware polyglots that work in HTML, SQL, template, and shell contexts
3. **Callback server** — catch executions via HTTP/DNS, correlate with injections
4. **Trigger engine** — attempt to cause execution (request pages, trigger exports, etc.)
5. **Correlation engine** — match callbacks to injection points, report findings

## Constraints

- **Zero dependencies**: Like venom-cache, standard library only (Python)
- **Safe by default**: Payloads phone home but don't cause damage
- **Portable**: Single file or simple install, works anywhere Python runs

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + zero deps | Consistency with venom-cache, portability | — Pending |
| CLI interface | Fits pentesting workflow, scriptable | — Pending |
| Built-in + Interactsh | Flexibility for local dev and real targets | — Pending |
| Detection only, not exploitation | Ethical boundary, reduces legal risk | — Pending |

---
*Last updated: 2026-01-29 after initialization*
