# Phase 2: HTTP Callback Server - Research

**Researched:** 2026-01-29
**Domain:** Python stdlib HTTP server for OOB vulnerability detection callbacks
**Confidence:** HIGH

## Summary

This phase implements an HTTP callback server using Python's stdlib `http.server` module to capture and correlate out-of-band (OOB) interactions from injected payloads. The server must accept any HTTP request, extract correlation IDs from URL paths, log the interaction, and persist it to the existing SQLite database.

Python's stdlib provides `ThreadingHTTPServer` (since 3.7) which handles concurrent requests and browser pre-opened connections without hanging. The existing `InjectionStore` already has the `callbacks` table schema ready for use. The correlation ID generator from Phase 1 produces 16-character hex IDs that are URL-safe and can be embedded in callback URLs like `http://attacker:8080/callback/{correlation_id}`.

**Primary recommendation:** Use `ThreadingHTTPServer` with a custom `BaseHTTPRequestHandler` subclass. Extract correlation IDs from URL path segments using `urllib.parse.urlparse()`. Use daemon threads for clean shutdown on Ctrl+C.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `http.server.ThreadingHTTPServer` | stdlib (3.7+) | Multi-threaded HTTP server | Handles concurrent callbacks without blocking |
| `http.server.BaseHTTPRequestHandler` | stdlib | Request handling base class | Standard pattern for custom HTTP handlers |
| `urllib.parse.urlparse` | stdlib | URL path parsing | Extract correlation ID from callback URL |
| `signal` | stdlib | Graceful shutdown | Handle SIGINT (Ctrl+C) for clean exit |
| `logging` | stdlib | Thread-safe logging | Already thread-safe, no setup needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading.Thread` | stdlib | Background server thread | If running server non-blocking |
| `selectors.DefaultSelector` | stdlib | Event loop for signal handling | Advanced graceful shutdown pattern |
| `socket.socketpair` | stdlib | Signal coordination | Inter-thread signal communication |
| `json` | stdlib | Header/body serialization | Storing callback metadata in DB |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadingHTTPServer | HTTPServer | Single-threaded; hangs with keep-alive connections |
| Custom handler | SimpleHTTPRequestHandler | Serves files; wrong use case |
| Manual threading | ForkingMixIn | Process per request; overkill, not Windows-compatible |

**Installation:**
```bash
# No installation needed - all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
ricochet/
├── server/
│   ├── __init__.py
│   ├── http.py           # CallbackServer, CallbackHandler classes
│   └── routes.py         # URL routing/correlation ID extraction (optional, can inline)
├── core/
│   ├── store.py          # Existing - add record_callback() method
│   └── correlation.py    # Existing - already has generate_correlation_id()
└── cli.py                # Add 'listen' subcommand with --http flag
```

### Pattern 1: Request Handler with Store Reference
**What:** Pass store instance to handler via server attribute
**When to use:** When handler needs database access
**Example:**
```python
# Source: Python socketserver docs pattern
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Access store via server instance
        store = self.server.store
        correlation_id = self._extract_correlation_id()
        if correlation_id:
            store.record_callback(correlation_id, self.client_address, self.path, dict(self.headers))
        self.send_response(200)
        self.end_headers()

class CallbackServer(ThreadingHTTPServer):
    daemon_threads = True  # Clean shutdown

    def __init__(self, server_address, store):
        super().__init__(server_address, CallbackHandler)
        self.store = store
```

### Pattern 2: Correlation ID Extraction from Path
**What:** Parse URL path to extract correlation ID
**When to use:** When correlation ID is in URL path segment
**Example:**
```python
# Source: urllib.parse docs
from urllib.parse import urlparse

def _extract_correlation_id(self) -> str | None:
    """Extract correlation ID from URL path.

    Supports formats:
    - /callback/{correlation_id}
    - /c/{correlation_id}
    - /{correlation_id}
    """
    parsed = urlparse(self.path)
    path = parsed.path.strip('/')
    parts = path.split('/')

    # Last segment is correlation ID
    if parts:
        candidate = parts[-1]
        # Validate: 16 hex chars
        if len(candidate) == 16 and all(c in '0123456789abcdef' for c in candidate):
            return candidate
    return None
```

### Pattern 3: Graceful Shutdown with Signal Handler
**What:** Handle SIGINT to stop server cleanly
**When to use:** Always - required for CLI tool usability
**Example:**
```python
# Source: Python signal docs
import signal
import threading

shutdown_event = threading.Event()

def signal_handler(signum, frame):
    print("\nShutting down...")
    shutdown_event.set()

def run_server(host: str, port: int, store):
    server = CallbackServer((host, port), store)
    server.timeout = 0.5  # Check shutdown every 0.5s

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Listening on http://{host}:{port}/")
    while not shutdown_event.is_set():
        server.handle_request()

    server.server_close()
```

### Pattern 4: Callback Record Structure
**What:** Store callback with full request details
**When to use:** For forensic analysis of what triggered callback
**Example:**
```python
# Add to ricochet/core/store.py
import json
import time

def record_callback(
    self,
    correlation_id: str,
    source_ip: str,
    request_path: str,
    headers: dict,
    body: bytes | None = None
) -> bool:
    """Record a callback, returning True if correlation ID was found."""
    with self._get_connection() as conn:
        # Check if injection exists (foreign key)
        exists = conn.execute(
            "SELECT 1 FROM injections WHERE id = ?",
            (correlation_id,)
        ).fetchone()

        if not exists:
            return False  # Unknown correlation ID

        conn.execute(
            """
            INSERT INTO callbacks (correlation_id, source_ip, request_path, headers, body, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (correlation_id, source_ip, request_path, json.dumps(headers), body, time.time())
        )
        return True
```

### Anti-Patterns to Avoid
- **Serving static files:** Don't extend SimpleHTTPRequestHandler - it's for file serving, invites path traversal
- **Blocking signal handlers:** Don't do I/O or database work in signal handlers - just set a flag
- **Single-threaded server:** Don't use HTTPServer alone - browsers keep connections alive and will block
- **Hardcoded paths:** Don't require exact `/callback/` prefix - correlation ID can be anywhere in path
- **Raising exceptions in handlers:** Don't let KeyboardInterrupt propagate from signal handlers in threaded code

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-threaded HTTP | Custom threading code | `ThreadingHTTPServer` | Handles thread lifecycle, daemon threads |
| URL parsing | String splitting only | `urllib.parse.urlparse()` | Handles query strings, fragments, edge cases |
| Thread-safe logging | Custom locks | `logging` module | Already thread-safe by design |
| Graceful shutdown | KeyboardInterrupt catch | `signal.signal()` + event flag | More reliable in threaded code |
| JSON serialization | Manual string building | `json.dumps()` | Handles escaping, encoding |

**Key insight:** Python's http.server module is production-ready for local testing servers. The threading is handled correctly, the request parsing is robust, and the patterns are well-documented.

## Common Pitfalls

### Pitfall 1: Server Blocks Forever on Keep-Alive Connections
**What goes wrong:** Using `HTTPServer` instead of `ThreadingHTTPServer`, server hangs waiting for browser to close connection
**Why it happens:** HTTP/1.1 keep-alive means browsers don't close connections; single-threaded server waits indefinitely
**How to avoid:** Always use `ThreadingHTTPServer`
**Warning signs:** Server stops responding after browser connects

### Pitfall 2: Shutdown Deadlock
**What goes wrong:** Calling `server.shutdown()` from the same thread running `serve_forever()`
**Why it happens:** `shutdown()` waits for `serve_forever()` to return, which can't happen if same thread
**How to avoid:** Either run server in background thread and call `shutdown()` from main, or use `handle_request()` loop with timeout
**Warning signs:** Ctrl+C hangs instead of stopping

### Pitfall 3: Lost Callbacks Due to Unknown Correlation IDs
**What goes wrong:** Callback arrives but correlation ID wasn't registered (injection not stored first)
**Why it happens:** User tests callback URL directly, or injection storage failed silently
**How to avoid:** Log ALL callbacks even if correlation ID unknown; provide warning in output
**Warning signs:** Callbacks received but no matches in status output

### Pitfall 4: Header Storage Encoding Issues
**What goes wrong:** Binary or non-UTF8 headers cause database errors
**Why it happens:** HTTP headers can contain arbitrary bytes in some edge cases
**How to avoid:** Use `json.dumps()` with `default=str` or encode headers safely
**Warning signs:** Database write errors on certain requests

### Pitfall 5: Path Traversal via Handler Extension
**What goes wrong:** If extending SimpleHTTPRequestHandler for any reason, path traversal vulnerabilities
**Why it happens:** SimpleHTTPRequestHandler is designed to serve files
**How to avoid:** Extend `BaseHTTPRequestHandler` directly; never serve files
**Warning signs:** N/A - just don't do it

### Pitfall 6: Non-Daemon Threads Prevent Exit
**What goes wrong:** Server doesn't exit cleanly on Ctrl+C; hangs waiting for request threads
**Why it happens:** `daemon_threads` defaults to `False` in ThreadingMixIn
**How to avoid:** Set `daemon_threads = True` on server class
**Warning signs:** Ctrl+C doesn't exit immediately if requests are in-flight

## Code Examples

Verified patterns from official sources:

### Complete Callback Handler
```python
# Source: http.server and signal docs patterns
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
import logging
import signal
import threading
import time

logger = logging.getLogger(__name__)

class CallbackHandler(BaseHTTPRequestHandler):
    """Handle incoming callback requests."""

    def log_message(self, format, *args):
        """Override to use logging module instead of stderr."""
        logger.info("%s - %s", self.address_string(), format % args)

    def _extract_correlation_id(self) -> str | None:
        """Extract 16-char hex correlation ID from URL path."""
        parsed = urlparse(self.path)
        parts = parsed.path.strip('/').split('/')
        if parts:
            candidate = parts[-1]
            if len(candidate) == 16 and all(c in '0123456789abcdef' for c in candidate):
                return candidate
        return None

    def _handle_callback(self, body: bytes | None = None):
        """Common callback handling for all HTTP methods."""
        correlation_id = self._extract_correlation_id()
        source_ip = self.client_address[0]

        if correlation_id:
            found = self.server.store.record_callback(
                correlation_id=correlation_id,
                source_ip=source_ip,
                request_path=self.path,
                headers=dict(self.headers),
                body=body
            )
            if found:
                logger.info("CALLBACK RECEIVED: %s from %s", correlation_id, source_ip)
            else:
                logger.warning("Unknown correlation ID: %s from %s", correlation_id, source_ip)
        else:
            logger.debug("Request without correlation ID: %s", self.path)

        # Always return 200 - don't leak info about valid/invalid IDs
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self._handle_callback()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length else None
        self._handle_callback(body)

    def do_HEAD(self):
        self._handle_callback()

    # Support any HTTP method - OOB interactions can use any method
    def do_PUT(self): self._handle_callback()
    def do_DELETE(self): self._handle_callback()
    def do_OPTIONS(self): self._handle_callback()
    def do_PATCH(self): self._handle_callback()
```

### Server with Graceful Shutdown
```python
# Source: socketserver and signal docs
class CallbackServer(ThreadingHTTPServer):
    """HTTP server for receiving OOB callbacks."""
    daemon_threads = True  # Clean exit without waiting for threads

    def __init__(self, server_address, store):
        super().__init__(server_address, CallbackHandler)
        self.store = store
        self._shutdown_event = threading.Event()

    def serve_until_shutdown(self):
        """Run server until shutdown is requested."""
        while not self._shutdown_event.is_set():
            self.handle_request()

    def request_shutdown(self):
        """Request graceful shutdown."""
        self._shutdown_event.set()


def run_callback_server(host: str, port: int, store) -> int:
    """Run callback server with graceful shutdown on SIGINT."""
    server = CallbackServer((host, port), store)

    def shutdown_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        server.request_shutdown()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print(f"Callback server listening on http://{host}:{port}/")
    print("Press Ctrl+C to stop")
    print()

    try:
        server.serve_until_shutdown()
    finally:
        server.server_close()

    return 0
```

### CLI Integration
```python
# Add to cli.py
def add_listen_command(subparsers):
    listen_parser = subparsers.add_parser(
        'listen',
        help='Start callback server to receive OOB interactions'
    )
    listen_parser.add_argument(
        '--http',
        action='store_true',
        help='Start HTTP callback server'
    )
    listen_parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    listen_parser.add_argument(
        '-p', '--port',
        type=int,
        default=8080,
        help='Port to listen on (default: 8080)'
    )
    listen_parser.set_defaults(func=cmd_listen)


def cmd_listen(args, store) -> int:
    """Handle listen subcommand."""
    if args.http:
        from ricochet.server.http import run_callback_server
        return run_callback_server(args.host, args.port, store)
    else:
        print("Error: specify --http to start HTTP callback server", file=sys.stderr)
        return 2
```

### Query Callbacks
```python
# Add to store.py
@dataclass
class CallbackRecord:
    """Record of a received callback."""
    id: int
    correlation_id: str
    source_ip: str
    request_path: str
    headers: dict
    body: bytes | None
    received_at: float


def get_callbacks_for_injection(self, correlation_id: str) -> list[CallbackRecord]:
    """Get all callbacks for a specific injection."""
    with self._get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM callbacks WHERE correlation_id = ? ORDER BY received_at DESC",
            (correlation_id,)
        ).fetchall()

    return [
        CallbackRecord(
            id=row['id'],
            correlation_id=row['correlation_id'],
            source_ip=row['source_ip'],
            request_path=row['request_path'],
            headers=json.loads(row['headers']) if row['headers'] else {},
            body=row['body'],
            received_at=row['received_at']
        )
        for row in rows
    ]


def get_injections_with_callbacks(self) -> list[tuple[InjectionRecord, int]]:
    """Get all injections that have received callbacks, with count."""
    with self._get_connection() as conn:
        rows = conn.execute(
            """
            SELECT i.*, COUNT(c.id) as callback_count
            FROM injections i
            JOIN callbacks c ON i.id = c.correlation_id
            GROUP BY i.id
            ORDER BY MAX(c.received_at) DESC
            """
        ).fetchall()

    return [
        (InjectionRecord(
            id=row['id'],
            target_url=row['target_url'],
            parameter=row['parameter'],
            payload=row['payload'],
            timestamp=row['injected_at'],
            context=row['context']
        ), row['callback_count'])
        for row in rows
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTTPServer + ThreadingMixIn | ThreadingHTTPServer | Python 3.7 | Simpler code, same functionality |
| Catching KeyboardInterrupt | signal.signal() handlers | Always preferred | More reliable in threaded code |
| Manual daemon_threads setup | Class attribute | Always available | Cleaner, declarative |

**Deprecated/outdated:**
- `SocketServer` module: Renamed to `socketserver` (lowercase) in Python 3
- `BaseHTTPServer`, `CGIHTTPServer`: Merged into `http.server` in Python 3

## Open Questions

Things that couldn't be fully resolved:

1. **HTTPS Support**
   - What we know: Python 3.14 adds `HTTPSServer` to stdlib; before that need `ssl.wrap_socket()`
   - What's unclear: Whether stdlib HTTPS is sufficient for testing or needs external certs
   - Recommendation: Implement HTTP first; HTTPS can be added in future phase using `ssl` module

2. **DNS Callback Server**
   - What we know: Full OOB detection needs DNS exfiltration support
   - What's unclear: Whether stdlib can handle DNS (probably needs external or manual UDP)
   - Recommendation: Out of scope for this phase; could be Phase 3 or 4

3. **Rate Limiting / DoS Protection**
   - What we know: A malicious target could flood the callback server
   - What's unclear: Whether this is a real concern for a local testing tool
   - Recommendation: Log a warning if callback rate exceeds threshold; don't implement full protection

## Sources

### Primary (HIGH confidence)
- [Python http.server documentation](https://docs.python.org/3/library/http.server.html) - ThreadingHTTPServer, BaseHTTPRequestHandler
- [Python socketserver documentation](https://docs.python.org/3/library/socketserver.html) - shutdown(), serve_forever(), daemon_threads
- [Python signal documentation](https://docs.python.org/3/library/signal.html) - SIGINT/SIGTERM handling, threading caveats
- [Python urllib.parse documentation](https://docs.python.org/3/library/urllib.parse.html) - urlparse(), parse_qs()

### Secondary (MEDIUM confidence)
- [Burp Collaborator documentation](https://portswigger.net/burp/documentation/collaborator) - Correlation ID design patterns
- [Interactsh GitHub](https://github.com/projectdiscovery/interactsh) - OOB server architecture reference

### Tertiary (LOW confidence)
- Various blog posts on Python HTTP servers (verified against official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, official docs consulted
- Architecture: HIGH - Follows documented patterns from Python docs
- Pitfalls: HIGH - Based on documented behavior and known issues

**Research date:** 2026-01-29
**Valid until:** 2026-03-01 (stable stdlib, 30-day validity)
