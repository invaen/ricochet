# Phase 4: Injection Engine - Research

**Researched:** 2026-01-29
**Domain:** HTTP request construction, payload injection, rate limiting
**Confidence:** HIGH (stdlib-only constraint well-documented)

## Summary

The Injection Engine requires parsing raw HTTP request files (Burp format), constructing HTTP requests with injected payloads, managing rate limiting, and tracking all injections via the existing InjectionStore. Python's stdlib provides all necessary tools: `urllib.request` for HTTP client operations, `http.client.parse_headers()` for header parsing, `urllib.parse` for URL manipulation, and `time` module for rate limiting.

The Burp request file format is simply a raw HTTP request (method, path, headers, body) with CRLF line endings. Injection vectors include query parameters, headers (especially User-Agent, Referer, X-Forwarded-For), cookies, and body fields. The existing correlation ID system (16-char hex) integrates naturally via placeholder substitution.

**Primary recommendation:** Build a request parser that extracts all injectable vectors, a payload injector that substitutes correlation IDs into payloads, and a rate-limited HTTP client using urllib.request with token bucket algorithm.

## Standard Stack

The established libraries/tools for this domain (stdlib only per constraint):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `urllib.request` | stdlib | HTTP client operations | Only stdlib HTTP client option |
| `urllib.parse` | stdlib | URL parsing/construction | parse_qs, urlencode, urlparse |
| `http.client` | stdlib | parse_headers, HTTPMessage | RFC 5322 header parsing |
| `io.BytesIO` | stdlib | Buffer for header parsing | Required by parse_headers |
| `time` | stdlib | Rate limiting timestamps | Token bucket implementation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ssl` | stdlib | HTTPS context configuration | Custom TLS settings |
| `json` | stdlib | JSON body handling | application/json content-type |
| `re` | stdlib | Placeholder substitution | Finding {{CALLBACK}} markers |
| `threading.Lock` | stdlib | Thread-safe rate limiting | Concurrent injection |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| urllib.request | http.client.HTTPConnection | Lower-level, more control but more code |
| Token bucket | sleep() delays | Simpler but doesn't allow bursting |
| Regex substitution | str.replace() | Less flexible for multiple placeholder formats |

**Installation:**
```bash
# No installation needed - all stdlib
python -c "import urllib.request, urllib.parse, http.client"
```

## Architecture Patterns

### Recommended Project Structure
```
ricochet/
├── injection/
│   ├── __init__.py
│   ├── parser.py        # Burp request file parser
│   ├── injector.py      # Payload injection logic
│   ├── http_client.py   # Rate-limited HTTP client
│   └── vectors.py       # Input vector extraction
├── core/
│   ├── store.py         # (existing) InjectionStore
│   └── correlation.py   # (existing) ID generation
└── cli.py               # (existing) add inject subcommand
```

### Pattern 1: Request File Parser
**What:** Parse raw HTTP request files into structured Request objects
**When to use:** Processing Burp-exported request files
**Example:**
```python
# Source: Python stdlib + Burp format analysis
import io
from http.client import parse_headers
from dataclasses import dataclass
from typing import Optional

CRLF = '\r\n'

@dataclass
class ParsedRequest:
    method: str
    path: str
    http_version: str
    headers: dict[str, str]
    body: Optional[bytes]
    host: str  # extracted from Host header

def parse_request_file(content: bytes) -> ParsedRequest:
    """Parse a Burp-format raw HTTP request file."""
    # Split into lines
    lines = content.split(b'\r\n')
    if not lines:
        raise ValueError("Empty request file")

    # Parse request line: "GET /path HTTP/1.1"
    request_line = lines[0].decode('utf-8', errors='replace')
    parts = request_line.split(' ', 2)
    method = parts[0]
    path = parts[1] if len(parts) > 1 else '/'
    http_version = parts[2] if len(parts) > 2 else 'HTTP/1.1'

    # Find header/body boundary (empty line)
    header_end = content.find(b'\r\n\r\n')
    if header_end == -1:
        header_bytes = content[len(lines[0]) + 2:]
        body = None
    else:
        header_bytes = content[len(lines[0]) + 2:header_end + 2]
        body = content[header_end + 4:]
        if not body:
            body = None

    # Parse headers using stdlib
    fp = io.BytesIO(header_bytes)
    msg = parse_headers(fp)
    headers = dict(msg.items())

    host = headers.get('Host', headers.get('host', 'localhost'))

    return ParsedRequest(
        method=method,
        path=path,
        http_version=http_version,
        headers=headers,
        body=body,
        host=host
    )
```

### Pattern 2: Input Vector Extraction
**What:** Identify all injectable parameters in a request
**When to use:** Discovering injection points automatically
**Example:**
```python
# Source: OWASP injection vectors + urllib.parse docs
from urllib.parse import urlparse, parse_qsl
from dataclasses import dataclass
from typing import Literal

@dataclass
class InjectionVector:
    location: Literal['query', 'header', 'cookie', 'body', 'path']
    name: str
    original_value: str

def extract_vectors(request: ParsedRequest) -> list[InjectionVector]:
    """Extract all injectable parameters from a request."""
    vectors = []

    # Query parameters
    parsed_url = urlparse(request.path)
    for name, value in parse_qsl(parsed_url.query, keep_blank_values=True):
        vectors.append(InjectionVector('query', name, value))

    # Interesting headers for injection
    injectable_headers = {
        'User-Agent', 'Referer', 'X-Forwarded-For', 'X-Forwarded-Host',
        'X-Custom-IP-Authorization', 'X-Original-URL', 'X-Rewrite-URL',
        'X-Client-IP', 'True-Client-IP', 'Forwarded'
    }
    for header_name in injectable_headers:
        if header_name in request.headers:
            vectors.append(InjectionVector('header', header_name, request.headers[header_name]))

    # Cookie parameters
    cookie_header = request.headers.get('Cookie', '')
    if cookie_header:
        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                name, value = cookie.strip().split('=', 1)
                vectors.append(InjectionVector('cookie', name, value))

    # Body parameters (form-urlencoded)
    content_type = request.headers.get('Content-Type', '')
    if request.body and 'application/x-www-form-urlencoded' in content_type:
        for name, value in parse_qsl(request.body.decode('utf-8', errors='replace')):
            vectors.append(InjectionVector('body', name, value))

    # JSON body handling requires manual parsing
    if request.body and 'application/json' in content_type:
        # Extract top-level string fields from JSON
        import json
        try:
            data = json.loads(request.body)
            if isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, str):
                        vectors.append(InjectionVector('body', key, val))
        except json.JSONDecodeError:
            pass

    return vectors
```

### Pattern 3: Token Bucket Rate Limiter
**What:** Rate limit HTTP requests to avoid target bans
**When to use:** All injection operations
**Example:**
```python
# Source: Token bucket algorithm, adapted from stdlib-only constraints
import time
import threading

class RateLimiter:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Tokens per second (requests/second)
            burst: Maximum burst size (default 1 = no bursting)
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, blocking: bool = True) -> bool:
        """Acquire a token, optionally blocking until available.

        Args:
            blocking: If True, wait for token. If False, return False immediately.

        Returns:
            True if token acquired, False if non-blocking and no token.
        """
        with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now

                # Refill tokens based on elapsed time
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

                if not blocking:
                    return False

                # Calculate wait time for next token
                wait_time = (1 - self.tokens) / self.rate

                # Release lock while sleeping
                self.lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self.lock.acquire()
```

### Pattern 4: HTTP Client with urllib.request
**What:** Send HTTP requests with custom method, headers, body
**When to use:** All injection HTTP operations
**Example:**
```python
# Source: Python urllib.request documentation
import urllib.request
import urllib.error
import ssl
from typing import Optional

@dataclass
class HttpResponse:
    status: int
    reason: str
    headers: dict[str, str]
    body: bytes
    url: str  # Final URL after redirects

def send_request(
    url: str,
    method: str = 'GET',
    headers: Optional[dict] = None,
    body: Optional[bytes] = None,
    timeout: float = 10.0,
    verify_ssl: bool = True
) -> HttpResponse:
    """Send HTTP request with full control over method, headers, body.

    Args:
        url: Full URL including scheme
        method: HTTP method
        headers: Request headers
        body: Request body as bytes
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
    """
    headers = headers or {}

    # Create request object
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    # Configure SSL context
    context = None
    if not verify_ssl:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            return HttpResponse(
                status=response.status,
                reason=response.reason,
                headers=dict(response.headers.items()),
                body=response.read(),
                url=response.url
            )
    except urllib.error.HTTPError as e:
        return HttpResponse(
            status=e.code,
            reason=e.reason,
            headers=dict(e.headers.items()),
            body=e.read(),
            url=url
        )
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect: {e.reason}")
```

### Anti-Patterns to Avoid
- **Hand-rolling HTTP parsing:** Use `http.client.parse_headers()` instead of manual parsing
- **Blocking rate limits without threading:** Use `time.sleep()` outside of locks
- **Ignoring HTTP redirects:** Default behavior may leak injected data to other hosts
- **Hardcoding injection points:** Extract vectors dynamically, allow user override

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP header parsing | Custom line splitting | `http.client.parse_headers()` | RFC 5322 compliant, handles edge cases |
| URL query parsing | `split('&')` | `urllib.parse.parse_qsl()` | Handles encoding, blank values, duplicates |
| URL reconstruction | String concatenation | `urllib.parse.urlunparse()` | Proper encoding, preserves structure |
| Form body encoding | Manual string building | `urllib.parse.urlencode()` | Handles special characters correctly |
| Thread-safe timing | Manual lock management | `threading.Lock()` context manager | Prevents deadlocks, handles exceptions |

**Key insight:** URL and HTTP parsing have many edge cases (encoding, duplicate keys, malformed input). Stdlib functions handle these correctly; hand-rolled parsers will have bugs.

## Common Pitfalls

### Pitfall 1: CRLF vs LF Line Endings
**What goes wrong:** Burp exports use CRLF (`\r\n`), but reading files in text mode converts to LF
**Why it happens:** Platform-specific newline handling
**How to avoid:** Always read request files in binary mode (`rb`)
**Warning signs:** `parse_headers()` fails or returns incomplete headers

### Pitfall 2: Redirect Following Leaks Payloads
**What goes wrong:** Injected payloads follow redirects to third-party domains
**Why it happens:** urllib.request follows redirects by default
**How to avoid:** Build custom opener with no redirect handler, or limit redirect domains
**Warning signs:** Callbacks received from unexpected IPs

### Pitfall 3: Content-Length Mismatch After Injection
**What goes wrong:** Body length changes after injection, but Content-Length header unchanged
**Why it happens:** Injecting into body changes size
**How to avoid:** Recalculate Content-Length after any body modification
**Warning signs:** Truncated requests, 400 errors from target

### Pitfall 4: URL Encoding Double-Encoding
**What goes wrong:** Already-encoded characters get encoded again
**Why it happens:** Using `quote()` on already-quoted strings
**How to avoid:** Decode first, then re-encode the whole string
**Warning signs:** `%2520` appearing instead of `%20`

### Pitfall 5: Rate Limiter Not Thread-Safe
**What goes wrong:** Concurrent requests exceed rate limit
**Why it happens:** Race condition in token bucket without locks
**How to avoid:** Use `threading.Lock()` around all token operations
**Warning signs:** Target returns 429s despite rate limiting

### Pitfall 6: Timeout Not Set
**What goes wrong:** Requests hang indefinitely on unresponsive targets
**Why it happens:** urllib.request has no default timeout
**How to avoid:** Always pass explicit `timeout` parameter
**Warning signs:** CLI hangs, zombie processes

## Code Examples

Verified patterns from official sources:

### Reconstructing URL with Injected Query Parameter
```python
# Source: Python urllib.parse documentation
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def inject_query_param(url: str, param: str, payload: str) -> str:
    """Replace a query parameter value with payload."""
    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)

    new_params = []
    for name, value in params:
        if name == param:
            new_params.append((name, payload))
        else:
            new_params.append((name, value))

    new_query = urlencode(new_params)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
```

### Building Request from Parsed File
```python
# Source: Python urllib.request documentation
def build_url(request: ParsedRequest, use_https: bool = False) -> str:
    """Construct full URL from parsed request."""
    scheme = 'https' if use_https else 'http'
    # Host header may include port
    host = request.host
    if ':' in host:
        netloc = host
    else:
        netloc = host
    return f"{scheme}://{netloc}{request.path}"

def execute_parsed_request(
    request: ParsedRequest,
    rate_limiter: RateLimiter,
    timeout: float = 10.0
) -> HttpResponse:
    """Execute a parsed request with rate limiting."""
    rate_limiter.acquire()  # Block until token available

    url = build_url(request)
    return send_request(
        url=url,
        method=request.method,
        headers=request.headers,
        body=request.body,
        timeout=timeout
    )
```

### Placeholder Substitution for Payloads
```python
# Source: Standard practice for templated payloads
import re
from ricochet.core.correlation import generate_correlation_id

def substitute_callback_url(
    payload: str,
    callback_base: str,
    correlation_id: str = None
) -> tuple[str, str]:
    """Replace {{CALLBACK}} placeholder with actual callback URL.

    Args:
        payload: Payload template with {{CALLBACK}} placeholder
        callback_base: Base URL for callbacks (e.g., http://attacker.com)
        correlation_id: Specific ID to use, or generate new one

    Returns:
        Tuple of (payload with URL, correlation_id used)
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()

    callback_url = f"{callback_base.rstrip('/')}/{correlation_id}"

    # Support multiple placeholder formats
    result = payload.replace('{{CALLBACK}}', callback_url)
    result = result.replace('{{callback}}', callback_url)
    result = result.replace('{CALLBACK}', callback_url)
    result = re.sub(r'\$\{CALLBACK\}', callback_url, result)

    return result, correlation_id
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| urllib2 (Python 2) | urllib.request (Python 3) | Python 3.0 | Unified into urllib package |
| Manual header parsing | http.client.parse_headers | Python 3 | RFC-compliant parsing |
| requests library | urllib.request | N/A (constraint) | Stdlib-only requirement |
| sleep-based rate limit | Token bucket | N/A | Allows burst while maintaining average rate |

**Deprecated/outdated:**
- `httplib` module: Renamed to `http.client` in Python 3
- `urllib2`: Merged into `urllib.request` in Python 3
- `urlparse` module: Merged into `urllib.parse` in Python 3

## Open Questions

Things that couldn't be fully resolved:

1. **Multipart Form Data Encoding**
   - What we know: `urllib.parse.urlencode()` handles application/x-www-form-urlencoded
   - What's unclear: Stdlib-only approach for multipart/form-data encoding
   - Recommendation: Implement minimal multipart encoder if needed, or document limitation

2. **HTTP/2 Support**
   - What we know: urllib.request only supports HTTP/1.1
   - What's unclear: Whether targets require HTTP/2
   - Recommendation: Document HTTP/1.1 limitation; most injection targets support it

3. **Proxy Support**
   - What we know: urllib.request supports proxies via ProxyHandler
   - What's unclear: Whether this phase needs proxy support
   - Recommendation: Add optional --proxy flag using ProxyHandler

## Sources

### Primary (HIGH confidence)
- [Python urllib.request documentation](https://docs.python.org/3/library/urllib.request.html) - Request class, urlopen, timeouts, SSL context
- [Python urllib.parse documentation](https://docs.python.org/3/library/urllib.parse.html) - urlparse, parse_qsl, urlencode, urlunparse
- [Python http.client documentation](https://docs.python.org/3/library/http.client.html) - parse_headers, HTTPMessage

### Secondary (MEDIUM confidence)
- [sqlmap request file format](https://github.com/sqlmapproject/sqlmap/wiki/usage) - Burp-format request files
- [OWASP Host Header Injection](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/17-Testing_for_Host_Header_Injection) - Injection vector identification
- [NotSoSecure OOB Cheatsheet](https://notsosecure.com/out-band-exploitation-oob-cheatsheet) - Payload templates

### Tertiary (LOW confidence)
- [Medium article on token bucket](https://dev.to/satrobit/rate-limiting-using-the-token-bucket-algorithm-3cjh) - Algorithm explanation
- [GitHub Gist token bucket](https://gist.github.com/lgelo/164c97bd3b6d9f2d1893) - Reference implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib well-documented, constraint is clear
- Architecture: HIGH - Patterns derived from official Python docs
- Pitfalls: MEDIUM - Some based on common practice rather than official docs
- Payload templates: MEDIUM - Based on security community resources

**Research date:** 2026-01-29
**Valid until:** 2026-03-29 (60 days - stdlib is stable)
