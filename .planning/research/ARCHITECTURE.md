# Architecture Patterns

**Domain:** Second-order vulnerability detection / OAST-style scanner
**Researched:** 2026-01-29
**Confidence:** HIGH (patterns verified against Burp Collaborator, Interactsh, XSS Hunter implementations)

## Executive Summary

Ricochet is an OAST-style (Out-of-Band Application Security Testing) tool that detects second-order and blind vulnerabilities. The architecture follows proven patterns from Burp Collaborator, Interactsh, and XSS Hunter but simplified for zero-dependency Python implementation.

The core insight: **payloads fire asynchronously and unpredictably**. The architecture must handle:
1. Injection happening at time T
2. Callback arriving at time T+N (seconds to weeks later)
3. Correlation linking callback back to injection

## Recommended Architecture

```
+------------------+     +-------------------+     +------------------+
|   CLI Interface  |---->| Injection Engine  |---->| Target App       |
+------------------+     +-------------------+     +------------------+
        |                        |                         |
        |                        v                         |
        |               +-------------------+              |
        |               | Payload Generator |              |
        |               +-------------------+              |
        |                        |                         |
        |                        v                         |
        |               +-------------------+              |
        |               | Injection Store   |<-------------+
        |               | (SQLite/JSON)     |     (stores injection metadata)
        |               +-------------------+
        |                        ^
        |                        |
        v                        |
+------------------+     +-------------------+     +------------------+
| Trigger Engine   |     | Correlation       |<----| Callback Server  |
| (causes fires)   |     | Engine            |     | (HTTP + DNS)     |
+------------------+     +-------------------+     +------------------+
        |                        |                         ^
        |                        v                         |
        |               +-------------------+              |
        +-------------->| Report Generator  |              |
                        +-------------------+    Callbacks from target
                                                  (async, delayed)
```

### Core Data Flow

```
1. INJECTION PHASE
   CLI -> Injection Engine -> generates payloads with unique IDs
                           -> injects into target inputs
                           -> stores {id, url, param, timestamp, payload} in Injection Store

2. CALLBACK PHASE (async, may be immediate or days later)
   Target processes payload -> fires callback to Callback Server
   Callback Server -> extracts correlation ID from subdomain/path/body
                   -> stores {id, callback_time, source_ip, http_details}
                   -> notifies Correlation Engine

3. TRIGGER PHASE (optional, speeds up detection)
   Trigger Engine -> requests pages that might execute stored payloads
                  -> triggers exports, emails, admin actions
                  -> increases callback likelihood

4. CORRELATION PHASE
   Correlation Engine -> matches callback IDs to injection records
                      -> computes vulnerability details
                      -> generates report

5. REPORT PHASE
   Report Generator -> formats findings (JSON, text, HTML)
                    -> outputs to CLI
```

## Component Boundaries

| Component | Responsibility | Inputs | Outputs | Dependencies |
|-----------|---------------|--------|---------|--------------|
| **CLI** | Parse args, orchestrate workflow | User commands | Invokes engines | All engines |
| **Injection Engine** | Crawl target, identify inputs, inject | Target URL, config | Injection records | Payload Generator, Injection Store |
| **Payload Generator** | Create context-aware payloads with correlation IDs | Context hints, callback domain | Payload strings | None (pure functions) |
| **Callback Server** | Listen for HTTP/DNS, record interactions | Network traffic | Callback records | Injection Store (for correlation) |
| **Injection Store** | Persist injection/callback data | Records | Query results | None (stdlib sqlite3/json) |
| **Trigger Engine** | Cause stored payloads to execute | Target URLs, triggers | HTTP requests | None |
| **Correlation Engine** | Match callbacks to injections | Store queries | Vulnerability findings | Injection Store |
| **Report Generator** | Format findings for output | Findings | Formatted reports | None |

### Interface Contracts

```python
# Payload Generator -> string payloads
def generate_payload(context: str, callback_url: str, correlation_id: str) -> str:
    """Returns payload string with embedded correlation ID"""

# Injection Store -> CRUD for injection records
class InjectionStore:
    def record_injection(self, id: str, url: str, param: str, payload: str, timestamp: float) -> None
    def record_callback(self, id: str, source_ip: str, details: dict, timestamp: float) -> None
    def get_injection(self, id: str) -> Optional[InjectionRecord]
    def get_unmatched_callbacks(self) -> List[CallbackRecord]
    def get_findings(self) -> List[Finding]

# Callback Server -> event notification
class CallbackServer:
    def on_callback(self, callback: Callable[[str, dict], None]) -> None
    """Register callback handler for when interactions arrive"""
```

## Threading Model

**Critical constraint:** The callback server MUST run continuously while the scanner operates. This requires concurrent execution.

### Recommended: Threading with Queue

```
Main Thread
    |
    +-- starts Callback Server Thread (daemon)
    |       |
    |       +-- HTTP server on port 8080
    |       +-- DNS server on port 53 (if root/capabilities)
    |       +-- pushes callbacks to Queue
    |
    +-- runs Injection Engine (sequential)
    |       |
    |       +-- generates payloads
    |       +-- makes HTTP requests to target
    |       +-- stores injection records
    |
    +-- runs Trigger Engine (sequential)
    |
    +-- Correlation Engine polls Queue
    |       |
    |       +-- matches callbacks to injections
    |
    +-- generates report
    +-- signals shutdown to Callback Server
```

### Why Threading Over Asyncio

For zero-dependency Python:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **threading + Queue** | Simple, stdlib only, works with blocking HTTP libs | GIL limits parallelism (OK for I/O) | **Recommended** |
| **asyncio** | Better for high concurrency | Requires async HTTP client (external deps or complex code) | Not for zero-dep |
| **multiprocessing** | True parallelism | Complex IPC, overkill for this use case | Overkill |

### Implementation Pattern

```python
import threading
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler

class CallbackHandler(BaseHTTPRequestHandler):
    callback_queue = None  # Set by server

    def do_GET(self):
        # Extract correlation ID from path/subdomain
        correlation_id = self.extract_correlation_id()
        self.callback_queue.put({
            'id': correlation_id,
            'source_ip': self.client_address[0],
            'path': self.path,
            'headers': dict(self.headers),
            'timestamp': time.time()
        })
        self.send_response(200)
        self.end_headers()

def run_callback_server(port: int, callback_queue: queue.Queue):
    CallbackHandler.callback_queue = callback_queue
    server = HTTPServer(('0.0.0.0', port), CallbackHandler)
    server.serve_forever()

# Main thread
callback_queue = queue.Queue()
server_thread = threading.Thread(
    target=run_callback_server,
    args=(8080, callback_queue),
    daemon=True
)
server_thread.start()

# Run injection engine...
# Periodically check callback_queue for matches
```

## Correlation ID Design

The correlation ID is the critical link between injection and callback. Design after [Burp Collaborator](https://portswigger.net/burp/documentation/collaborator):

### ID Structure

```
Format: {random_prefix}.{injection_hash}.{callback_domain}
Example: a8f3b2.c7d9e1f4a2b3.callback.ricochet.local

Where:
- random_prefix: 6 chars, prevents ID enumeration
- injection_hash: 12 chars, hash of (target_url + param + timestamp + secret)
- callback_domain: your controlled domain
```

### Embedding in Payloads

```python
# HTTP callback payload
f'<img src="http://{correlation_id}.{callback_domain}/x.gif">'

# DNS callback payload (for firewall bypass)
f'<img src="http://{{{{.}}}}nslookup {correlation_id}.{callback_domain}{{{{.}}}}">'

# JavaScript callback
f'<script>new Image().src="http://{callback_domain}/{correlation_id}"</script>'
```

### Extraction on Callback

```python
def extract_correlation_id(self) -> str:
    # From subdomain: a8f3b2.c7d9e1f4a2b3.callback.example.com
    host = self.headers.get('Host', '')
    parts = host.split('.')
    if len(parts) >= 4:
        return f"{parts[0]}.{parts[1]}"

    # From path: /callback/a8f3b2.c7d9e1f4a2b3
    if self.path.startswith('/callback/'):
        return self.path.split('/')[2]

    return None
```

## Data Persistence

### Option 1: SQLite (Recommended for persistence)

```sql
CREATE TABLE injections (
    id TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    parameter TEXT NOT NULL,
    payload TEXT NOT NULL,
    context TEXT,  -- html, url, header, etc.
    injected_at REAL NOT NULL
);

CREATE TABLE callbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT NOT NULL,
    source_ip TEXT,
    request_path TEXT,
    headers TEXT,  -- JSON
    body TEXT,
    received_at REAL NOT NULL,
    FOREIGN KEY (correlation_id) REFERENCES injections(id)
);

CREATE INDEX idx_callbacks_correlation ON callbacks(correlation_id);
```

### Option 2: JSON Files (Simpler, no sqlite3 dependency issues)

```
.ricochet/
    injections.jsonl     # One JSON object per line
    callbacks.jsonl      # One JSON object per line
```

**Recommendation:** SQLite. It's in Python stdlib (`sqlite3`), supports concurrent reads, and enables efficient correlation queries.

## Patterns to Follow

### Pattern 1: Correlation-First Payload Design

**What:** Every payload embeds a correlation ID before injection.

**When:** Always. This is non-negotiable for second-order detection.

**Example:**
```python
def inject_xss(target_url: str, param: str, callback_domain: str, store: InjectionStore):
    correlation_id = generate_correlation_id()
    payload = f'"><script>new Image().src="http://{callback_domain}/{correlation_id}"</script>'

    # Record BEFORE injection (injection might fail, but ID is reserved)
    store.record_injection(
        id=correlation_id,
        url=target_url,
        param=param,
        payload=payload,
        timestamp=time.time()
    )

    # Now inject
    inject_payload(target_url, param, payload)
```

### Pattern 2: Callback Domain Flexibility

**What:** Support multiple callback methods for different network environments.

**When:** Always. Targets have varying firewall rules.

**Methods (in order of reliability):**
1. **DNS callbacks** - Most likely to succeed (DNS often allowed outbound)
2. **HTTP to IP** - Works if egress HTTP allowed
3. **HTTPS with valid cert** - Required for some contexts (mixed content blocking)

### Pattern 3: Graceful Degradation

**What:** Continue operation even if components fail.

**When:** Callback server can't bind port, DNS not available, etc.

**Example:**
```python
def start_callback_servers(config):
    servers = []

    # Try HTTP
    try:
        http_server = start_http_callback(config.http_port)
        servers.append(http_server)
    except OSError as e:
        log.warning(f"HTTP callback server failed: {e}")

    # Try DNS (requires root or capabilities)
    try:
        dns_server = start_dns_callback(53)
        servers.append(dns_server)
    except PermissionError:
        log.warning("DNS callback requires root - skipping")

    if not servers:
        raise RuntimeError("No callback servers could start")

    return servers
```

### Pattern 4: Deferred Correlation

**What:** Don't require immediate callback. Support long-running scans.

**When:** Second-order vulns may fire hours/days later.

**Implementation:**
```python
# Allow running correlation independently
ricochet scan --target https://example.com  # Injects, waits 5min, reports
ricochet listen --duration 24h              # Just runs callback server
ricochet correlate                          # Matches stored callbacks to injections
ricochet report                             # Generates report from stored data
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous Callback Waiting

**What:** Blocking main thread waiting for callbacks after each injection.

**Why bad:** Second-order vulns don't fire immediately. You'll timeout and miss them.

**Instead:** Fire-and-forget injection, continuous callback collection, batch correlation.

### Anti-Pattern 2: In-Memory Only Storage

**What:** Storing injections/callbacks only in memory.

**Why bad:**
- Process crash loses all data
- Can't correlate callbacks that arrive after scanner exits
- Can't resume interrupted scans

**Instead:** Persist to SQLite immediately. Memory is cache, disk is truth.

### Anti-Pattern 3: Single Callback Method

**What:** Only supporting HTTP callbacks.

**Why bad:** Firewalls commonly block outbound HTTP but allow DNS.

**Instead:** Support HTTP, HTTPS, and DNS callbacks. DNS is most reliable for exfiltration.

### Anti-Pattern 4: Predictable Correlation IDs

**What:** Sequential IDs like `inj_001`, `inj_002`.

**Why bad:** Attackers can enumerate other users' injections on shared callback servers.

**Instead:** Cryptographically random IDs with hash-based verification (see Burp Collaborator pattern).

### Anti-Pattern 5: Blocking DNS Resolution in Scan Loop

**What:** Doing DNS lookups for each injection target synchronously.

**Why bad:** DNS can be slow, blocks the scan.

**Instead:** Cache DNS results, or use IP addresses directly when possible.

## Scalability Considerations

| Concern | Single Target | 10 Targets | 100+ Targets |
|---------|--------------|------------|--------------|
| **Injection throughput** | Sequential OK | Sequential OK | Consider thread pool |
| **Callback server** | Single thread OK | Single thread OK | May need connection pooling |
| **Storage** | SQLite file | SQLite file | SQLite with WAL mode |
| **Correlation** | On-demand | On-demand | Background thread |
| **Memory** | ~10MB | ~50MB | ~200MB (mostly payload cache) |

For Ricochet's scope (CLI tool, single user), single-threaded injection with threaded callback server is sufficient.

## Build Order (Dependency-Driven)

Based on component dependencies, build in this order:

```
Phase 1: Foundation
├── Injection Store (no deps, needed by everything)
├── Payload Generator (no deps, pure functions)
└── Correlation ID utilities (no deps)

Phase 2: Callback Infrastructure
├── HTTP Callback Server (needs Store)
└── DNS Callback Server (needs Store, optional)

Phase 3: Injection
├── Input Discovery (crawling/parsing)
├── Injection Engine (needs Payload Generator, Store)
└── Context Detection (determines which payloads to use)

Phase 4: Trigger & Correlation
├── Trigger Engine (optional, improves detection)
├── Correlation Engine (needs Store)
└── Report Generator (needs Correlation Engine)

Phase 5: Integration
├── CLI Interface (orchestrates all components)
└── End-to-end testing
```

### Rationale

1. **Store first** - Everything writes to or reads from it
2. **Payloads second** - Needed before injection can work
3. **Callback server third** - Must be running before injections start
4. **Injection fourth** - Core functionality, requires 1-3
5. **Correlation/reporting last** - Consumes outputs of other components

## Suggested Module Structure

```
ricochet/
├── __init__.py
├── __main__.py           # CLI entry point
├── cli.py                # Argument parsing, orchestration
├── config.py             # Configuration dataclasses
│
├── core/
│   ├── __init__.py
│   ├── correlation.py    # ID generation, matching logic
│   └── store.py          # SQLite-based persistence
│
├── payloads/
│   ├── __init__.py
│   ├── generator.py      # Payload generation logic
│   ├── xss.py            # XSS-specific payloads
│   ├── sqli.py           # SQL injection payloads
│   ├── ssti.py           # Template injection payloads
│   └── cmdi.py           # Command injection payloads
│
├── callback/
│   ├── __init__.py
│   ├── server.py         # HTTP callback server
│   └── dns.py            # DNS callback server (optional)
│
├── scanner/
│   ├── __init__.py
│   ├── crawler.py        # URL/form discovery
│   ├── injector.py       # Injection execution
│   └── trigger.py        # Trigger engine
│
└── report/
    ├── __init__.py
    ├── formatter.py      # Output formatting
    └── templates/        # Report templates (text, json, html)
```

## Sources

**OAST Architecture:**
- [PortSwigger OAST Overview](https://portswigger.net/burp/application-security-testing/oast)
- [Burp Collaborator Documentation](https://portswigger.net/burp/documentation/collaborator)
- [Burp Collaborator Modern Elastic Design](https://portswigger.net/blog/a-modern-elastic-design-for-burp-collaborator-server)
- [Interactsh Release Blog](https://projectdiscovery.io/blog/interactsh-release)

**Blind XSS / Second-Order:**
- [XSS Hunter Express](https://github.com/mandatoryprogrammer/xsshunter-express)
- [XSS Hunter Client (Correlation)](https://github.com/mandatoryprogrammer/xsshunter_client)
- [Bugcrowd Blind XSS Guide](https://www.bugcrowd.com/blog/the-guide-to-blind-xss-advanced-techniques-for-bug-bounty-hunters-worth-250000/)
- [USENIX Second-Order Vulnerabilities Paper](https://www.usenix.org/system/files/conference/usenixsecurity14/sec14-paper-dahse.pdf)

**Python Concurrency:**
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Python Queue Documentation](https://docs.python.org/3/library/queue.html)
- [Thread Producer-Consumer Pattern](https://superfastpython.com/thread-producer-consumer-pattern-in-python/)
- [JetBrains Concurrency Guide](https://blog.jetbrains.com/pycharm/2025/06/concurrency-in-async-await-and-threading/)

**SQL Injection Detection:**
- [Second-Order SQL Injection Detection Methods](https://ieeexplore.ieee.org/document/8285104/)
- [NetSPI Second-Order SQLi with DNS](https://www.netspi.com/blog/technical-blog/web-application-pentesting/second-order-sql-injection-with-stored-procedures-dns-based-egress/)
