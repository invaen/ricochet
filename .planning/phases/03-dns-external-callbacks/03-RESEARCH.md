# Phase 3: DNS & External Callbacks - Research

**Researched:** 2026-01-29
**Domain:** DNS Protocol Implementation, Interactsh Integration
**Confidence:** HIGH (stdlib DNS), MEDIUM (Interactsh API)

## Summary

This phase adds two critical capabilities: a DNS callback server for firewall-bypassing detection and Interactsh integration for leveraging external OOB infrastructure. Both features enhance callback detection beyond HTTP-only scenarios.

The DNS server can be implemented using Python's stdlib only (`socketserver` + `struct`) following the DNS wire format (RFC 1035). The 12-byte header and question section are straightforward to parse. For correlation, we embed the 16-char hex correlation ID as a subdomain prefix (e.g., `a1b2c3d4e5f67890.callback.example.com`).

Interactsh integration requires implementing their encrypted polling API or using the existing Python client library. However, since ricochet requires zero external dependencies, we must implement a minimal client ourselves or make it an optional feature.

**Primary recommendation:** Implement stdlib-only DNS server with correlation ID as subdomain prefix. Make Interactsh integration optional (requires `requests` or similar for HTTPS).

## Standard Stack

### Core (Stdlib Only - DNS Server)

| Module | Purpose | Why Standard |
|--------|---------|--------------|
| `socketserver.UDPServer` | UDP server framework | Handles socket lifecycle, threading |
| `socketserver.ThreadingMixIn` | Concurrent request handling | Same pattern as HTTP server |
| `struct` | DNS packet parsing/building | Binary format handling |
| `socket` | Low-level UDP operations | Required for DNS protocol |

### Supporting (Optional - Interactsh)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `interactsh-client-python` | latest | Full Interactsh client | If external deps allowed |
| `urllib.request` | stdlib | HTTPS polling (limited) | Basic Interactsh polling |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom DNS parser | `dnslib` | External dep vs stdlib-only constraint |
| Custom Interactsh client | `interactsh-client-python` | External dep; has `disnake` dependency |
| UDP port 53 | Higher port (5353, 8053) | Avoids root, but clients must know alt port |

**Installation:**
```bash
# Core (no installation needed - stdlib only)

# Optional Interactsh client (if deps allowed):
pip install interactsh-client
```

## Architecture Patterns

### Recommended Project Structure
```
ricochet/
├── server/
│   ├── __init__.py
│   ├── http.py           # Existing HTTP callback server
│   └── dns.py            # NEW: DNS callback server
├── external/
│   ├── __init__.py
│   └── interactsh.py     # NEW: Interactsh client (optional)
└── cli.py                # Add --dns flag, --interactsh options
```

### Pattern 1: DNS Server with socketserver.UDPServer

**What:** Threaded UDP server that parses DNS queries and extracts correlation IDs from subdomains.

**When to use:** Always for DNS callback detection.

**Example:**
```python
# Source: Python docs socketserver + RFC 1035
import socketserver
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ricochet.core.store import InjectionStore


class DNSHandler(socketserver.BaseRequestHandler):
    """Handle DNS queries and extract correlation IDs from subdomains."""

    server: 'DNSCallbackServer'

    def handle(self) -> None:
        data, sock = self.request

        # Parse DNS query
        query = self._parse_query(data)
        if query:
            qname, qtype = query
            correlation_id = self._extract_correlation_id(qname)

            if correlation_id:
                self.server.store.record_callback(
                    correlation_id=correlation_id,
                    source_ip=self.client_address[0],
                    request_path=f"DNS:{qname}",
                    headers={"qtype": str(qtype)},
                    body=None
                )

            # Send response (always respond to avoid leaking info)
            response = self._build_response(data, qname, qtype)
            sock.sendto(response, self.client_address)

    def _parse_query(self, data: bytes) -> tuple[str, int] | None:
        """Parse DNS query, return (qname, qtype) or None."""
        if len(data) < 12:
            return None

        # Skip header (12 bytes), parse question
        offset = 12
        labels = []
        while offset < len(data):
            length = data[offset]
            if length == 0:
                offset += 1
                break
            if length >= 192:  # Compression pointer
                break
            labels.append(data[offset+1:offset+1+length].decode('ascii', errors='ignore'))
            offset += 1 + length

        qname = '.'.join(labels)

        # QTYPE is next 2 bytes
        if offset + 2 <= len(data):
            qtype = struct.unpack('!H', data[offset:offset+2])[0]
            return qname, qtype

        return None

    def _extract_correlation_id(self, qname: str) -> str | None:
        """Extract 16-char hex correlation ID from first subdomain."""
        parts = qname.lower().split('.')
        if not parts:
            return None

        candidate = parts[0]
        if len(candidate) == 16 and all(c in '0123456789abcdef' for c in candidate):
            return candidate
        return None

    def _build_response(self, query: bytes, qname: str, qtype: int) -> bytes:
        """Build DNS response with NXDOMAIN or minimal answer."""
        # Copy transaction ID from query
        txn_id = query[:2]

        # Response flags: QR=1, OPCODE=0, AA=1, TC=0, RD=1, RA=1, RCODE=0
        flags = struct.pack('!H', 0x8580)

        # Counts: 1 question, 1 answer, 0 authority, 0 additional
        counts = struct.pack('!HHHH', 1, 1, 0, 0)

        # Question section (copy from query)
        question = query[12:]  # Everything after header

        # Answer section - return 127.0.0.1 for A queries
        if qtype == 1:  # A record
            answer = (
                b'\xc0\x0c' +  # Pointer to qname in question
                struct.pack('!HHIH', 1, 1, 60, 4) +  # TYPE=A, CLASS=IN, TTL=60, RDLEN=4
                bytes([127, 0, 0, 1])  # 127.0.0.1
            )
        else:
            # For non-A queries, return empty answer
            answer = b''
            counts = struct.pack('!HHHH', 1, 0, 0, 0)

        return txn_id + flags + counts + question + answer


class DNSCallbackServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    """Threaded DNS server for callback detection."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], store: 'InjectionStore'):
        super().__init__(server_address, DNSHandler)
        self.store = store
```

### Pattern 2: Interactsh Polling Client (Minimal, Optional)

**What:** HTTP client that polls Interactsh server for interactions.

**When to use:** When user wants to use external callback infrastructure (firewalled environments).

**Example:**
```python
# Source: Interactsh API analysis from GitHub
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Iterator

@dataclass
class InteractshInteraction:
    """Represents a single Interactsh interaction."""
    protocol: str
    unique_id: str
    full_id: str
    raw_request: str
    remote_address: str
    timestamp: str


class InteractshClient:
    """Minimal Interactsh polling client (stdlib only, no encryption)."""

    # Note: Full Interactsh uses RSA+AES encryption
    # This minimal version only works with servers that allow unencrypted polling
    # or requires implementing the full crypto stack

    PUBLIC_SERVERS = [
        "oast.pro", "oast.live", "oast.site",
        "oast.online", "oast.fun", "oast.me"
    ]

    def __init__(self, server: str, correlation_id: str, secret: str):
        self.server = server
        self.correlation_id = correlation_id
        self.secret = secret
        self.base_url = f"https://{server}"

    def generate_subdomain(self, nonce: str = "") -> str:
        """Generate interaction subdomain."""
        return f"{self.correlation_id}{nonce}.{self.server}"

    def poll(self) -> Iterator[InteractshInteraction]:
        """Poll for interactions (simplified, may need encryption)."""
        url = f"{self.base_url}/poll?id={self.correlation_id}&secret={self.secret}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

                for item in data.get('data', []):
                    yield InteractshInteraction(
                        protocol=item.get('protocol', ''),
                        unique_id=item.get('unique-id', ''),
                        full_id=item.get('full-id', ''),
                        raw_request=item.get('raw-request', ''),
                        remote_address=item.get('remote-address', ''),
                        timestamp=item.get('timestamp', '')
                    )
        except urllib.error.URLError:
            return  # Silently fail on network errors
```

### Pattern 3: Subdomain Correlation Format

**What:** Embed correlation ID as subdomain prefix for DNS callbacks.

**Format:** `{correlation_id}.{user_domain}` or `{correlation_id}.callback.{user_domain}`

**Example:**
```
a1b2c3d4e5f67890.callback.example.com
^^^^^^^^^^^^^^^^ 16-char hex correlation ID
                 ^^^^^^^^ optional namespace
                          ^^^^^^^^^^^ user's callback domain
```

**Why this format:**
- First label is always the correlation ID (easy extraction)
- Compatible with wildcard DNS (`*.callback.example.com`)
- URL-safe hex chars work in all DNS contexts
- 16 chars is short enough to avoid DNS label limits (63 chars max)

### Anti-Patterns to Avoid

- **Parsing DNS with regex:** Use struct for binary protocol, not string manipulation
- **Hardcoding IP responses:** Make response IP configurable (or use NXDOMAIN)
- **Blocking on DNS receive:** Use threading or async for concurrent requests
- **Ignoring query types:** Log QTYPE for debugging (A=1, AAAA=28, TXT=16)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full DNS library | Complete DNS parser | Parse only what's needed (question section) | DNS is complex; we only need subdomain extraction |
| Interactsh crypto | RSA+AES implementation | Optional external client or limited polling | Crypto is hard; use battle-tested code |
| UDP socket management | Raw socket handling | `socketserver.UDPServer` | Handles lifecycle, threading, address reuse |

**Key insight:** For callback detection, we don't need a full DNS server - just enough to receive queries and extract correlation IDs. Similarly, for Interactsh, we may need to accept limited functionality without full encryption support.

## Common Pitfalls

### Pitfall 1: Port 53 Requires Root

**What goes wrong:** DNS server fails to bind on port 53 without elevated privileges.

**Why it happens:** Ports below 1024 are privileged on Unix systems.

**How to avoid:**
1. Default to high port (5353 or 8053) for development
2. Document that production use on port 53 requires:
   - Running as root (not recommended)
   - Using `CAP_NET_BIND_SERVICE` capability
   - Using port forwarding (iptables/nftables)
   - Running in Docker with `--privileged` or port mapping

**Warning signs:** `OSError: [Errno 13] Permission denied`

### Pitfall 2: DNS Response Required

**What goes wrong:** DNS clients timeout and retry when no response sent.

**Why it happens:** DNS is request-response; clients expect answers.

**How to avoid:** Always send a response, even for unknown correlation IDs.
- Return NXDOMAIN or minimal A record
- This also prevents enumeration (same behavior for valid/invalid IDs)

**Warning signs:** Multiple identical queries from same source

### Pitfall 3: Interactsh Encryption Complexity

**What goes wrong:** Polling fails because public servers require encrypted communication.

**Why it happens:** Interactsh uses RSA-2048 for key exchange and AES-256-CTR for payloads.

**How to avoid:**
1. Make Interactsh integration optional (requires external dependency)
2. Or implement full crypto stack (complex, ~200 lines)
3. Or only support self-hosted servers with encryption disabled

**Warning signs:** Empty poll results, 401 errors, JSON parse failures

### Pitfall 4: DNS Label Length Limits

**What goes wrong:** Queries with long subdomains are truncated or rejected.

**Why it happens:** DNS labels are limited to 63 characters each, total name to 253.

**How to avoid:** Keep correlation IDs short (16 chars is safe). Don't allow user-supplied prefixes that could exceed limits.

**Warning signs:** Truncated correlation IDs, failed lookups

## Code Examples

### DNS Header Parsing
```python
# Source: RFC 1035, routley.io DNS guide
import struct

def parse_dns_header(data: bytes) -> dict:
    """Parse 12-byte DNS header."""
    if len(data) < 12:
        raise ValueError("Data too short for DNS header")

    fields = struct.unpack('!HHHHHH', data[:12])

    return {
        'id': fields[0],
        'flags': fields[1],
        'qdcount': fields[2],  # Question count
        'ancount': fields[3],  # Answer count
        'nscount': fields[4],  # Authority count
        'arcount': fields[5],  # Additional count
    }

# Flag bit extraction
def parse_flags(flags: int) -> dict:
    return {
        'qr': (flags >> 15) & 1,      # 0=query, 1=response
        'opcode': (flags >> 11) & 0xF, # 0=standard query
        'aa': (flags >> 10) & 1,       # Authoritative answer
        'tc': (flags >> 9) & 1,        # Truncated
        'rd': (flags >> 8) & 1,        # Recursion desired
        'ra': (flags >> 7) & 1,        # Recursion available
        'rcode': flags & 0xF,          # Response code (0=no error)
    }
```

### DNS Name Decoding
```python
# Source: RFC 1035 Section 4.1.2
def decode_dns_name(data: bytes, offset: int) -> tuple[str, int]:
    """Decode DNS name from wire format.

    Returns (name, new_offset) where new_offset is position after name.
    Handles compression pointers.
    """
    labels = []
    jumped = False
    original_offset = offset
    max_offset = offset

    while True:
        if offset >= len(data):
            break

        length = data[offset]

        if length == 0:
            # End of name
            if not jumped:
                max_offset = offset + 1
            break

        if (length & 0xC0) == 0xC0:
            # Compression pointer
            if offset + 1 >= len(data):
                break
            pointer = struct.unpack('!H', data[offset:offset+2])[0] & 0x3FFF
            if not jumped:
                max_offset = offset + 2
            offset = pointer
            jumped = True
            continue

        # Regular label
        if offset + 1 + length > len(data):
            break
        labels.append(data[offset+1:offset+1+length].decode('ascii', errors='ignore'))
        offset += 1 + length

    return '.'.join(labels), max_offset
```

### CLI Integration Pattern
```python
# Add to ricochet/cli.py
def cmd_listen(args, store) -> int:
    """Handle listen subcommand."""
    if args.http:
        from ricochet.server.http import run_callback_server
        return run_callback_server(args.host, args.port, store)
    elif args.dns:
        from ricochet.server.dns import run_dns_server
        return run_dns_server(args.host, args.dns_port, store)
    elif args.interactsh:
        from ricochet.external.interactsh import run_interactsh_poller
        return run_interactsh_poller(args.interactsh_server, store)
    else:
        print("Error: specify --http, --dns, or --interactsh", file=sys.stderr)
        return 2

# Add arguments to listen_parser:
listen_parser.add_argument('--dns', action='store_true', help='Start DNS callback server')
listen_parser.add_argument('--dns-port', type=int, default=5353, help='DNS port (default: 5353)')
listen_parser.add_argument('--interactsh', action='store_true', help='Poll Interactsh server')
listen_parser.add_argument('--interactsh-server', default='oast.pro', help='Interactsh server')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Burp Collaborator only | Interactsh (open source) | 2021 | Free OOB testing |
| DNS-only callbacks | Multi-protocol (DNS, HTTP, SMTP, LDAP) | 2021 | More detection vectors |
| Unencrypted polling | RSA+AES encrypted polling | 2021+ | Prevents interception |

**Deprecated/outdated:**
- Relying solely on HTTP callbacks (easily blocked by firewalls)
- Using predictable correlation IDs (enumeration risk)

## Open Questions

1. **Interactsh Encryption**
   - What we know: Public servers require RSA+AES encryption
   - What's unclear: Can we implement minimal crypto with stdlib only?
   - Recommendation: Make optional dependency, document limitation

2. **DNS Response Strategy**
   - What we know: Must respond to avoid client retries
   - What's unclear: Best response for security (NXDOMAIN vs real IP)
   - Recommendation: Return configurable IP (default 127.0.0.1) for A queries, NXDOMAIN for others

3. **Wildcard DNS Setup**
   - What we know: Users need wildcard DNS for their domain
   - What's unclear: Best documentation approach
   - Recommendation: Include setup guide in docs (out of scope for this phase)

## Sources

### Primary (HIGH confidence)
- [Python socketserver docs](https://docs.python.org/3/library/socketserver.html) - UDPServer, ThreadingMixIn patterns
- [Python struct docs](https://docs.python.org/3/library/struct.html) - Binary packing format
- [RFC 1035](https://datatracker.ietf.org/doc/html/rfc1035) - DNS protocol specification
- [Hand-writing DNS messages](https://routley.io/posts/hand-writing-dns-messages) - DNS wire format tutorial

### Secondary (MEDIUM confidence)
- [Interactsh GitHub](https://github.com/projectdiscovery/interactsh) - Server/client architecture
- [interactsh-client-python](https://github.com/justinsteven/interactsh-client-python) - Python client reference
- [ProjectDiscovery Interactsh docs](https://docs.projectdiscovery.io/opensource/interactsh/overview) - Feature overview

### Tertiary (LOW confidence)
- [Wikipedia DNS record types](https://en.wikipedia.org/wiki/List_of_DNS_record_types) - QTYPE values reference

## Metadata

**Confidence breakdown:**
- DNS server implementation: HIGH - stdlib documented, RFC stable
- DNS parsing/building: HIGH - binary format well-documented
- Interactsh polling API: MEDIUM - undocumented, reverse-engineered from source
- Interactsh encryption: LOW - complex crypto, may need external deps

**Research date:** 2026-01-29
**Valid until:** 90 days (DNS protocol stable, Interactsh may update)
