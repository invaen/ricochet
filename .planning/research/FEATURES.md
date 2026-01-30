# Feature Landscape: Second-Order Vulnerability Detection

**Domain:** CLI tool for detecting second-order vulnerabilities (XSS, SQLi, SSTI, Command Injection)
**Target Users:** Bug bounty hunters, penetration testers
**Researched:** 2026-01-29
**Confidence:** MEDIUM (synthesized from multiple tool analyses and community patterns)

---

## Table Stakes

Features users expect from a second-order vulnerability detection tool. Missing any of these makes the tool feel incomplete or unprofessional.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Out-of-Band Callback Detection** | Core mechanism for blind/second-order vuln confirmation. Industry standard via Burp Collaborator, Interactsh. Without OOB, tool is just a payload injector. | High | Must support DNS + HTTP callbacks minimum. DNS bypasses most firewalls. |
| **Interactsh Integration** | De facto open-source standard for OAST. Nuclei, ZAP, Caido all integrate it. Bug bounty hunters expect it. | Medium | Both hosted (oast.pro/me/fun) and self-hosted server support needed. |
| **Multiple Vulnerability Types** | Competitors like Dalfox, sqlmap, tplmap, commix each handle one type. A unified tool must cover the big four: XSS, SQLi, SSTI, Command Injection. | High | Each vuln type has different payload sets and detection logic. |
| **Request File Input** | Burp Suite workflow is dominant. Hunters save requests from Burp, feed to specialized tools. sqlmap `-r`, Dalfox file mode all support this. | Medium | Support raw HTTP request format (Burp export). |
| **CLI Interface** | Bug bounty automation is CLI-centric. Tools chain via pipes (subfinder \| httpx \| nuclei). No CLI = no automation integration. | Low | Follow Unix philosophy: stdin/stdout, exit codes, machine-parseable output. |
| **Payload Customization** | Every target is different. WAF bypasses, encoding variations, custom contexts. Dalfox has `--custom-payload`, sqlmap has tamper scripts. | Medium | Load payloads from file, support custom payload syntax. |
| **Output Formats** | Hunters need JSON for automation, plain text for quick review, markdown for reports. Standard across security tools. | Low | JSON, plain text minimum. Consider markdown/HTML for reports. |
| **Verbose/Debug Mode** | When things don't work, hunters need to understand why. Every mature tool has `-v`, `-vv`, `-vvv` levels. | Low | Show payloads sent, responses received, timing info. |
| **Timeout Controls** | Second-order vulns may trigger hours/days later. Default timeouts must be configurable. | Low | Per-request timeout + overall polling duration for OOB. |
| **Proxy Support** | Hunters route through Burp/Caido to inspect traffic. sqlmap `--proxy`, Dalfox `--proxy`. Table stakes for any HTTP tool. | Low | HTTP/SOCKS proxy, proxy authentication. |

---

## Differentiators

Features that set Ricochet apart from manual testing and existing tools. Not expected, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Unified Multi-Vuln Workflow** | No existing tool handles XSS + SQLi + SSTI + Command Injection second-order detection together. Hunters currently use 4+ separate tools. | High | This is Ricochet's core differentiator. Single tool, unified interface, comprehensive coverage. |
| **Automatic Injection-to-Trigger Correlation** | Track which specific injection caused which OOB callback. XSS Hunter does this for blind XSS. Nuclei does it for templates. No tool does it across multiple vuln types for second-order. | High | Requires unique identifiers in payloads. Critical for reporting. |
| **Trigger Point Suggestions** | Second-order vulns trigger in different contexts (admin panels, email handlers, PDF generators, log viewers). Suggest common trigger endpoints based on injection point. | Medium | Based on domain knowledge: contact forms -> admin ticket view, user profile -> admin user list, etc. |
| **Built-in Callback Server** | Interactsh requires external setup. Built-in server (like XSS Hunter) means zero-config OOB for simple cases. | Medium | Optional: for hunters who can't use external services or want simpler setup. |
| **Payload Fire Metadata Capture** | When blind XSS fires, capture: DOM snapshot, cookies, URL, user-agent, timestamp. XSS Hunter does this. Extend to other vuln types where applicable. | Medium | Valuable for proving impact, escalating severity. |
| **Session Management** | Authenticated testing requires cookie/header management. Persist sessions across injection + trigger phases. | Medium | Cookie jar, custom headers, session refresh hooks. |
| **Rate Limiting Awareness** | Aggressive scanning gets IPs banned. Smart rate limiting with adaptive backoff. | Low | Configurable delays, detect 429s, auto-throttle. |
| **Workflow Modes** | Different hunters have different workflows: full auto-crawl, targeted parameter injection, request file batch processing. | Medium | Mode switching: `crawl`, `targeted`, `file` modes mentioned in project context. |
| **Report Generation** | Auto-generate bug bounty report templates with PoC steps, payload used, evidence screenshots/data. Saves hours per finding. | Medium | Markdown output compatible with HackerOne/Bugcrowd. |
| **Trigger Mode Flexibility** | Passive (wait for natural trigger) vs Active (attempt to trigger via known paths). Some vulns only trigger on admin login, others on cron jobs. | Medium | Passive: long-polling OOB. Active: crawl trigger endpoints. |
| **Context-Aware Payloads** | Detect injection context (HTML attribute, JS string, SQL query) and use appropriate payloads. Dalfox does this for XSS. | High | Reduces noise, increases detection rate. |

---

## Anti-Features

Things to deliberately NOT build. Common mistakes in this domain that would waste effort or harm the tool.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **GUI Interface (Initially)** | Bug bounty hunters live in terminals. GUI adds massive complexity, slows iteration, fragments codebase. Burp/Caido already provide GUI proxy workflows. | CLI-first. Consider GUI later only if demand is clear. |
| **Exploitation/Post-Exploitation** | Detection tool, not exploitation framework. Commix/sqlmap handle exploitation. Adding shells, file read/write, etc. bloats scope and creates legal liability. | Detect and report. Let specialized tools handle exploitation. User can pipe findings to sqlmap/commix. |
| **Full Web Application Scanner** | Scope creep. Competing with Burp, Acunetix, ZAP is a losing battle. They have years of development, massive teams. | Focus on second-order detection niche. Do one thing excellently. |
| **Cloud-Hosted SaaS** | Requires infrastructure, billing, compliance. Many hunters work on sensitive targets, can't use third-party services. | Self-contained CLI tool. User controls all data. |
| **Browser Automation for All Triggers** | Headless browser is slow, resource-intensive, flaky. Unnecessary for most trigger detection. | HTTP-based trigger attempts first. Headless only for specific DOM-based scenarios. |
| **Machine Learning Detection** | ML requires training data, adds complexity, creates black-box behavior. Security tools need deterministic, explainable results. | Pattern-based detection. Clear payload-to-finding correlation. |
| **Real-time Collaboration** | Multi-user features add auth, sync, conflict resolution complexity. Solo hunters are primary audience. | Single-user CLI. Teams can share via git/config files. |
| **Integrated Asset Discovery** | subfinder, amass, httpx already excel at recon. Duplicating this work is wasteful. | Accept URLs/requests as input. Integrate into existing recon pipelines. |
| **WAF Evasion as Primary Feature** | Infinite cat-and-mouse game. Every WAF is different. Custom tamper scripts handle this better. | Support custom payloads and encoding. Don't promise "WAF bypass." |

---

## Feature Dependencies

```
Injection Input Methods
    |
    +-- Request File Input (Burp format)
    +-- URL/Parameter Input (CLI args)
    +-- Auto-Crawl Mode (discovers injection points)
            |
            v
Payload Generation & Injection
    |
    +-- Vuln-Specific Payloads (XSS, SQLi, SSTI, CMDi)
    +-- Custom Payload Support
    +-- Context Detection (optional, improves accuracy)
            |
            v
Out-of-Band Callback Handling  <---- CORE DEPENDENCY
    |
    +-- Interactsh Integration (external)
    +-- Built-in Callback Server (optional)
    +-- Correlation Engine (maps callbacks to injections)
            |
            v
Trigger Mechanisms
    |
    +-- Passive Polling (wait for OOB)
    +-- Active Trigger (crawl/request known endpoints)
            |
            v
Reporting & Output
    |
    +-- CLI Output (verbose, quiet modes)
    +-- JSON Export (automation)
    +-- Report Generation (bug bounty submissions)
```

**Critical Path:** OOB Callback Handling is the linchpin. Without reliable callback correlation, the tool cannot confirm second-order findings.

---

## MVP Recommendation

For MVP, prioritize delivering a working second-order detection workflow over breadth of features.

### Phase 1 (MVP) - Must Have:

1. **Interactsh Integration** - Use existing infrastructure, don't reinvent
2. **Request File Input** - Burp workflow compatibility
3. **XSS + SQLi Detection** - Most common second-order vulns in bug bounty
4. **Basic OOB Correlation** - Know which injection triggered which callback
5. **JSON + Plain Text Output** - Automation + human readable
6. **CLI with Essential Flags** - proxy, timeout, verbosity, output file

### Phase 2 - High Value:

1. **SSTI + Command Injection** - Complete the vulnerability coverage
2. **Built-in Callback Server** - Zero-config alternative to Interactsh
3. **Active Trigger Mode** - Don't just inject, also trigger
4. **Custom Payload Support** - Adapt to specific targets/WAFs
5. **Report Generation** - Save hours per finding

### Defer to Post-MVP:

- **Auto-Crawl Mode** - Complex, can use external tools (katana, gospider)
- **Context-Aware Payloads** - Nice to have, not essential for detection
- **Session Management** - Manual cookie/header flags work initially
- **Payload Fire Metadata** - XSS Hunter territory, nice enhancement later

---

## Competitive Landscape Summary

| Tool | Focus | Second-Order Support | Ricochet Advantage |
|------|-------|---------------------|-------------------|
| **Burp Suite** | General web testing | Good (Collaborator) | Free, CLI, multi-vuln unified |
| **sqlmap** | SQL injection | `--second-url` flag | Broader vuln coverage |
| **Dalfox** | XSS | `--blind` flag for blind XSS | SQLi, SSTI, CMDi coverage |
| **tplmap/SSTImap** | SSTI | Limited | XSS, SQLi, CMDi coverage |
| **Commix** | Command injection | OOB via DNS/HTTP | XSS, SQLi, SSTI coverage |
| **XSS Hunter** | Blind XSS | Excellent | Broader vuln types, CLI |
| **Nuclei** | Template-based scanning | Interactsh templates | Specialized second-order workflow |

**Ricochet's Gap:** No single open-source CLI tool unifies second-order detection for XSS, SQLi, SSTI, and Command Injection with proper correlation. Hunters currently cobble together multiple tools or rely on expensive Burp Suite Pro.

---

## Sources

**OAST and Interactsh:**
- [ProjectDiscovery Interactsh Documentation](https://docs.projectdiscovery.io/tools/interactsh/overview)
- [Nuclei + Interactsh Integration](https://projectdiscovery.io/blog/nuclei-interactsh-integration)
- [PortSwigger OAST Overview](https://portswigger.net/burp/application-security-testing/oast)

**Blind XSS Tools:**
- [Bugcrowd Guide to Blind XSS](https://www.bugcrowd.com/blog/the-guide-to-blind-xss-advanced-techniques-for-bug-bounty-hunters-worth-250000/)
- [Intigriti Blind XSS Guide](https://www.intigriti.com/researchers/blog/hacking-tools/hunting-for-blind-cross-site-scripting-xss-vulnerabilities-a-complete-guide)
- [XSS Hunter GitHub](https://github.com/mandatoryprogrammer/xsshunter)

**Second-Order SQL Injection:**
- [HackTricks Second-Order SQLi with sqlmap](https://book.hacktricks.xyz/pentesting-web/sql-injection/sqlmap/second-order-injection-sqlmap)
- [PortSwigger Second-Order SQL Injection](https://portswigger.net/kb/issues/00100210_sql-injection-second-order)

**Vulnerability Scanners:**
- [Dalfox GitHub](https://github.com/hahwul/dalfox)
- [Commix Project](https://commixproject.com/)
- [Tplmap GitHub](https://github.com/epinna/tplmap)
- [sqlmap Usage](https://github.com/sqlmapproject/sqlmap/wiki/usage)

**Bug Bounty Workflows:**
- [Bugcrowd Systemic vs Manual Approaches](https://www.bugcrowd.com/blog/the-two-faces-of-bug-bounty-hunting-systemic-vs-manual-approaches/)
- [Bug Bounty Automation 2025](https://www.eicta.iitk.ac.in/knowledge-hub/ethical-hacking/bug-bounty-automation)
