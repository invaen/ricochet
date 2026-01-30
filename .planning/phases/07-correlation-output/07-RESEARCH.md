# Phase 7: Correlation & Output - Research

**Researched:** 2026-01-30
**Domain:** Callback correlation, security tool output formats, verbose logging, HTTP proxy support
**Confidence:** HIGH

## Summary

Phase 7 implements the correlation engine that joins callbacks with their originating injections, and provides multiple output formats for reporting findings. The existing database schema already supports correlation via the `correlation_id` foreign key relationship. The primary work is: (1) building a correlation query that joins injections and callbacks, (2) implementing JSON and text output formatters following security tool conventions, (3) adding verbose/debug logging using Python's logging module with `-v/-vv` patterns, and (4) adding HTTP proxy support via `urllib.request.ProxyHandler`.

The standard approach for security tool output follows patterns established by Nuclei, ffuf, and sqlmap: JSON output uses newline-delimited JSON (JSONL) for streaming, includes metadata about the scan, and provides detailed finding objects. Text output should be human-readable with clear severity indicators and structured sections.

**Primary recommendation:** Implement correlation as a SQL JOIN query on `correlation_id`, output JSON in JSONL format with finding objects containing injection details + callback details + timing, use Python's logging module with verbosity mapped to log levels (WARNING default, INFO for -v, DEBUG for -vv), and add proxy support via `urllib.request.ProxyHandler` with `--proxy` CLI argument.

## Standard Stack

The established libraries/tools for this domain (all Python stdlib):

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` | stdlib | JSON serialization | Standard for security tool output; no external dependencies |
| `logging` | stdlib | Debug/verbose output | Built-in log levels, formatters, handlers; well-understood patterns |
| `urllib.request.ProxyHandler` | stdlib | HTTP proxy support | Native urllib integration; supports HTTP/HTTPS proxies |
| `sqlite3` | stdlib | Correlation queries | Already in use; JOIN queries for correlation |
| `datetime` | stdlib | Timestamp formatting | ISO 8601 format for JSON output |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `textwrap` | stdlib | Text formatting | Wrapping long lines in text output |
| `sys.stdout`/`sys.stderr` | stdlib | Output streams | stdout for findings, stderr for logs/progress |
| `time` | stdlib | Timing calculations | Time delta between injection and callback |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONL | Full JSON array | JSONL enables streaming; full JSON requires buffering all results |
| logging module | print() statements | logging provides levels, formatters, and proper stderr handling |
| ProxyHandler | requests library | requests is external dependency; ProxyHandler is stdlib |
| Custom text format | SARIF | SARIF is complex and meant for static analysis; simpler text is appropriate |

**Installation:**
```bash
# No installation needed - stdlib only
```

## Architecture Patterns

### Recommended Project Structure

```
ricochet/
├── core/
│   ├── store.py          # Existing - add correlation queries
│   └── correlation.py    # Existing - add finding generation
├── output/
│   ├── __init__.py
│   ├── formatters.py     # JSON, text, verbose formatters
│   └── finding.py        # Finding dataclass
└── cli.py                # Add -o, --proxy, enhance -v
```

### Pattern 1: Correlation via SQL JOIN

**What:** Query injections and callbacks using INNER JOIN on correlation_id to find successful callbacks.

**When to use:** When generating findings - only injections that received callbacks are findings.

**Example:**
```python
# Source: Python sqlite3 documentation + existing store.py patterns
def get_correlated_findings(self) -> list[Finding]:
    """Get all injections that received callbacks with full details."""
    with self._get_connection() as conn:
        rows = conn.execute("""
            SELECT
                i.id as correlation_id,
                i.target_url,
                i.parameter,
                i.payload,
                i.context,
                i.injected_at,
                c.id as callback_id,
                c.source_ip,
                c.request_path,
                c.headers as callback_headers,
                c.body as callback_body,
                c.received_at,
                (c.received_at - i.injected_at) as delay_seconds
            FROM injections i
            INNER JOIN callbacks c ON i.id = c.correlation_id
            ORDER BY c.received_at DESC
        """).fetchall()

    return [self._row_to_finding(row) for row in rows]
```

### Pattern 2: JSONL Output Format

**What:** Newline-delimited JSON where each line is a complete JSON object.

**When to use:** For JSON output (`-o json`) - enables streaming and easy parsing.

**Example:**
```python
# Source: Nuclei/ffuf output format patterns
import json
import sys
from datetime import datetime

def output_jsonl(findings: list[Finding], file=sys.stdout) -> None:
    """Output findings in JSONL format (one JSON object per line)."""
    for finding in findings:
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": "ricochet",
            "finding": {
                "correlation_id": finding.correlation_id,
                "severity": finding.severity,
                "injection": {
                    "target_url": finding.target_url,
                    "parameter": finding.parameter,
                    "payload": finding.payload,
                    "context": finding.context,
                    "injected_at": finding.injected_at,
                },
                "callback": {
                    "source_ip": finding.source_ip,
                    "request_path": finding.request_path,
                    "received_at": finding.received_at,
                    "delay_seconds": finding.delay_seconds,
                },
            }
        }
        print(json.dumps(record), file=file)
```

### Pattern 3: Verbose Logging with -v/-vv

**What:** Map argparse count action to logging levels.

**When to use:** Always - standard CLI pattern for controlling output verbosity.

**Example:**
```python
# Source: https://xahteiwi.eu/resources/hints-and-kinks/python-cli-logging-options/
import logging
import argparse

def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbosity: Count from argparse (0=warning, 1=info, 2+=debug)
    """
    # Map verbosity to log level: 0->WARNING, 1->INFO, 2+->DEBUG
    level = logging.WARNING - (verbosity * 10)
    level = max(level, logging.DEBUG)  # Don't go below DEBUG

    # Configure format based on level
    if level <= logging.DEBUG:
        fmt = '%(asctime)s %(levelname)s %(name)s: %(message)s'
    else:
        fmt = '%(levelname)s: %(message)s'

    logging.basicConfig(
        level=level,
        format=fmt,
        stream=sys.stderr,  # Logs to stderr, findings to stdout
    )
```

### Pattern 4: HTTP Proxy Support via ProxyHandler

**What:** Use urllib.request.ProxyHandler to route traffic through HTTP proxies (Burp, ZAP).

**When to use:** When `--proxy` argument is provided.

**Example:**
```python
# Source: https://docs.python.org/3/library/urllib.request.html
import urllib.request
import ssl

def create_opener_with_proxy(
    proxy_url: str | None = None,
    verify_ssl: bool = True
) -> urllib.request.OpenerDirector:
    """Create urllib opener with optional proxy support.

    Args:
        proxy_url: Proxy URL (e.g., http://127.0.0.1:8080)
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Configured OpenerDirector
    """
    handlers = []

    # Proxy handler
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url,
        })
        handlers.append(proxy_handler)
    else:
        # Disable environment proxy detection
        handlers.append(urllib.request.ProxyHandler({}))

    # SSL context for unverified connections
    if not verify_ssl:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=context))

    return urllib.request.build_opener(*handlers)
```

### Pattern 5: Finding Dataclass

**What:** Structured dataclass representing a correlated finding.

**When to use:** As the common data structure between correlation query and output formatters.

**Example:**
```python
# Source: Python dataclasses documentation
from dataclasses import dataclass
from typing import Optional

@dataclass
class Finding:
    """A correlated finding representing a successful callback."""

    # Correlation
    correlation_id: str

    # Injection details
    target_url: str
    parameter: str
    payload: str
    context: Optional[str]
    injected_at: float

    # Callback details
    callback_id: int
    source_ip: str
    request_path: str
    callback_headers: dict
    callback_body: Optional[bytes]
    received_at: float

    # Derived
    delay_seconds: float

    @property
    def severity(self) -> str:
        """Derive severity from context/payload type."""
        if 'ssti' in self.context.lower() if self.context else False:
            return 'high'
        if 'sqli' in self.context.lower() if self.context else False:
            return 'high'
        if 'xss' in self.context.lower() if self.context else False:
            return 'medium'
        return 'info'
```

### Anti-Patterns to Avoid

- **Buffering all findings in memory:** Don't load all findings before outputting. Stream JSONL line by line.
- **Mixing logs and findings on stdout:** Don't print log messages to stdout. Use stderr for logs, stdout for findings.
- **Hardcoding proxy settings:** Don't assume proxy presence. Make it optional with `--proxy`.
- **Ignoring SSL errors silently:** Don't swallow SSL errors. Log them at DEBUG level.
- **Custom log levels:** Don't create custom logging levels. Use standard DEBUG/INFO/WARNING/ERROR.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Manual string formatting | `json.dumps()` | Handles escaping, Unicode, special values |
| Log level management | Custom verbosity flags | `logging.setLevel()` | Standard levels, thread-safe, configurable |
| Proxy configuration | Manual socket handling | `urllib.request.ProxyHandler` | Handles HTTP CONNECT, auth, headers |
| Timestamp formatting | `strftime()` strings | `datetime.isoformat()` | ISO 8601 standard, timezone aware |
| Output stream selection | Custom file handling | `sys.stdout`/`sys.stderr` | Proper encoding, buffering, piping |

**Key insight:** Python's logging module is specifically designed for the verbose/debug use case. Don't reimplement log levels with print statements and conditionals.

## Common Pitfalls

### Pitfall 1: Proxy with HTTPS Targets

**What goes wrong:** HTTPS requests through proxy fail with SSL errors because proxy certificate isn't trusted.

**Why it happens:** Intercepting proxies (Burp, ZAP) use their own certificates for HTTPS inspection.

**How to avoid:** When `--proxy` is set, automatically disable SSL verification (with warning) or provide `--insecure` flag.

**Warning signs:** `ssl.SSLCertVerificationError` when using proxy with HTTPS targets.

### Pitfall 2: Log Messages in JSON Output

**What goes wrong:** JSON output is corrupted because log messages are mixed in.

**Why it happens:** Both logging and findings written to stdout.

**How to avoid:** Always configure `logging.basicConfig(stream=sys.stderr)`. Only findings go to stdout.

**Warning signs:** JSON parse errors when piping output to `jq` or other tools.

### Pitfall 3: Missing Callbacks Show as Errors

**What goes wrong:** Injections without callbacks are incorrectly flagged as errors.

**Why it happens:** Confusing "no callback yet" with "injection failed".

**How to avoid:** Distinguish between injections (attempted) and findings (callbacks received). An injection without a callback is normal - callbacks may arrive later or not at all.

**Warning signs:** User confusion about what "successful" means.

### Pitfall 4: Timezone Handling in Timestamps

**What goes wrong:** Timestamps are inconsistent or wrong when comparing injection time to callback time.

**Why it happens:** Mixing local time and UTC, or not recording timezone.

**How to avoid:** Always use UTC internally (`time.time()` returns UTC epoch). Format as ISO 8601 with `Z` suffix for output.

**Warning signs:** Delay calculations are off by hours (timezone offset).

### Pitfall 5: Verbose Mode Slows Performance

**What goes wrong:** DEBUG logging with payload/response content makes the tool unusably slow.

**Why it happens:** Logging large strings (full HTTP responses) is expensive.

**How to avoid:** Truncate large values in log messages. Only log full content at highest verbosity or on request.

**Warning signs:** Tool runs much slower with `-vv` than without.

## Code Examples

Verified patterns from official sources and security tool conventions:

### Text Output Format

```python
# Source: Nuclei/ffuf text output conventions
from datetime import datetime

def output_text(findings: list[Finding], verbose: bool = False) -> None:
    """Output findings in human-readable text format."""

    if not findings:
        print("No findings.")
        return

    print(f"=== Ricochet Findings ({len(findings)}) ===")
    print()

    for i, f in enumerate(findings, 1):
        # Severity indicator
        severity_icons = {
            'high': '[!]',
            'medium': '[+]',
            'low': '[*]',
            'info': '[-]',
        }
        icon = severity_icons.get(f.severity, '[-]')

        print(f"{icon} Finding #{i}")
        print(f"    Correlation ID: {f.correlation_id}")
        print(f"    Target: {f.target_url}")
        print(f"    Parameter: {f.parameter}")
        print(f"    Severity: {f.severity.upper()}")
        print(f"    Delay: {f.delay_seconds:.2f}s")
        print()

        if verbose:
            print(f"    Payload: {f.payload}")
            print(f"    Callback from: {f.source_ip}")
            print(f"    Callback path: {f.request_path}")
            print()
```

### CLI Argument Additions

```python
# Source: argparse documentation + existing cli.py patterns
def create_parser() -> argparse.ArgumentParser:
    # ... existing code ...

    # Global options
    parser.add_argument(
        '-o', '--output',
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--proxy',
        metavar='URL',
        help='HTTP proxy URL (e.g., http://127.0.0.1:8080)'
    )

    # findings subcommand
    findings_parser = subparsers.add_parser(
        'findings',
        help='Show correlated findings'
    )
    findings_parser.add_argument(
        '--since',
        metavar='HOURS',
        type=float,
        help='Only show findings from last N hours'
    )
    findings_parser.add_argument(
        '--min-severity',
        choices=['info', 'low', 'medium', 'high'],
        default='info',
        help='Minimum severity to show (default: info)'
    )
    findings_parser.set_defaults(func=cmd_findings)

    return parser
```

### Correlation Engine

```python
# Source: sqlite3 documentation + existing store.py patterns
def get_findings(
    self,
    since: float | None = None,
    min_severity: str = 'info'
) -> list[Finding]:
    """Get correlated findings with optional filters.

    Args:
        since: Unix timestamp - only findings after this time
        min_severity: Minimum severity level

    Returns:
        List of Finding objects ordered by callback time (newest first)
    """
    query = """
        SELECT
            i.id as correlation_id,
            i.target_url,
            i.parameter,
            i.payload,
            i.context,
            i.injected_at,
            c.id as callback_id,
            c.source_ip,
            c.request_path,
            c.headers as callback_headers,
            c.body as callback_body,
            c.received_at,
            (c.received_at - i.injected_at) as delay_seconds
        FROM injections i
        INNER JOIN callbacks c ON i.id = c.correlation_id
    """

    params = []
    conditions = []

    if since is not None:
        conditions.append("c.received_at > ?")
        params.append(since)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY c.received_at DESC"

    with self._get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    findings = []
    for row in rows:
        finding = Finding(
            correlation_id=row['correlation_id'],
            target_url=row['target_url'],
            parameter=row['parameter'],
            payload=row['payload'],
            context=row['context'],
            injected_at=row['injected_at'],
            callback_id=row['callback_id'],
            source_ip=row['source_ip'],
            request_path=row['request_path'],
            callback_headers=json.loads(row['callback_headers']) if row['callback_headers'] else {},
            callback_body=row['callback_body'],
            received_at=row['received_at'],
            delay_seconds=row['delay_seconds'],
        )

        # Filter by severity
        severity_order = {'info': 0, 'low': 1, 'medium': 2, 'high': 3}
        if severity_order.get(finding.severity, 0) >= severity_order.get(min_severity, 0):
            findings.append(finding)

    return findings
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| XML output | JSON/JSONL | ~2015 | JSON is universal, easier to parse |
| Single JSON file | JSONL (streaming) | ~2020 | Enables large result sets, streaming |
| Custom log levels | Standard logging | Always | Interoperability, familiarity |
| Manual proxy handling | ProxyHandler | Python 2.7+ | Built-in, reliable |
| Print debugging | logging module | Python 2.3+ | Proper levels, filtering, formatting |

**Deprecated/outdated:**
- XML output formats for security tools (JSON is standard)
- Custom verbosity implementations (use logging module)
- Environment-only proxy configuration (CLI flag is more explicit)

## Open Questions

Things that couldn't be fully resolved:

1. **SARIF Support**
   - What we know: SARIF is an OASIS standard for static analysis results
   - What's unclear: Whether SARIF is appropriate for dynamic/OOB findings
   - Recommendation: Skip SARIF for now; it's designed for static analysis. JSON/text covers the use case.

2. **Severity Classification**
   - What we know: Severity should be derived from vulnerability type
   - What's unclear: Exact mapping (is SSTI always high? What about polyglot?)
   - Recommendation: Start with simple context-based mapping, allow user override

3. **Multiple Callbacks per Injection**
   - What we know: An injection can trigger multiple callbacks (e.g., DNS then HTTP)
   - What's unclear: Should this be one finding or multiple?
   - Recommendation: One finding per callback (user can see the full picture)

## Sources

### Primary (HIGH confidence)

- [Python urllib.request documentation](https://docs.python.org/3/library/urllib.request.html) - ProxyHandler class, build_opener, SSL context
- [Python logging documentation](https://docs.python.org/3/library/logging.html) - Log levels, basicConfig, formatters
- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html) - JOIN queries, Row factory
- Existing ricochet codebase - store.py patterns, cli.py structure

### Secondary (MEDIUM confidence)

- [Nuclei output format](https://github.com/projectdiscovery/nuclei) - JSONL pattern, field structure
- [ffuf output format](https://github.com/ffuf/ffuf) - JSON fields, result structure
- [Python CLI logging patterns](https://xahteiwi.eu/resources/hints-and-kinks/python-cli-logging-options/) - -v/-vv mapping to log levels

### Tertiary (LOW confidence)

- Web search results for security tool output conventions (2025-2026)
- SARIF specification (not directly applicable to OOB detection)

## Metadata

**Confidence breakdown:**
- Correlation engine: HIGH - Simple SQL JOIN on existing schema
- JSON output: HIGH - Standard JSONL pattern from official tools
- Text output: HIGH - Follows established security tool conventions
- Verbose logging: HIGH - Standard Python logging patterns
- Proxy support: HIGH - urllib.request.ProxyHandler is well-documented

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (stable domain, 30 days)
