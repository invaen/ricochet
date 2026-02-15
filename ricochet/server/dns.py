"""DNS callback server for capturing OOB interactions via DNS queries."""

import logging
import signal
import socketserver
import struct
import threading
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ricochet.core.store import InjectionStore

logger = logging.getLogger(__name__)

# DNS constants
DNS_HEADER_SIZE = 12
QTYPE_A = 1
QCLASS_IN = 1


class DNSHandler(socketserver.BaseRequestHandler):
    """UDP request handler that captures DNS queries and extracts correlation IDs."""

    server: 'DNSCallbackServer'  # Type hint for the server reference

    def handle(self) -> None:
        """Handle an incoming DNS query."""
        data, socket = self.request
        client_ip = self.client_address[0]

        if len(data) < DNS_HEADER_SIZE:
            logger.debug("Packet too short from %s", client_ip)
            return

        try:
            # Parse DNS header
            txn_id = struct.unpack('!H', data[:2])[0]

            # Parse question section
            qname, qtype, offset = self._parse_question(data, DNS_HEADER_SIZE)

            if qname is None:
                logger.debug("Failed to parse QNAME from %s", client_ip)
                response = self._build_response(txn_id, data, None, 0)
                socket.sendto(response, self.client_address)
                return

            # Extract correlation ID from first subdomain label
            correlation_id = self._extract_correlation_id(qname)

            if correlation_id:
                # Record the callback
                recorded = self.server.store.record_callback(
                    correlation_id=correlation_id,
                    source_ip=client_ip,
                    request_path=f"DNS:{qname}",
                    headers={"qtype": str(qtype)},
                    body=None
                )

                if recorded:
                    logger.info(
                        "DNS callback received: correlation_id=%s source=%s qname=%s",
                        correlation_id, client_ip, qname
                    )
                else:
                    logger.warning(
                        "Unknown DNS correlation ID: %s from %s",
                        correlation_id, client_ip
                    )
            else:
                logger.debug(
                    "DNS query without correlation ID from %s: %s",
                    client_ip, qname
                )

            # Build and send response
            response = self._build_response(txn_id, data, qname, qtype)
            socket.sendto(response, self.client_address)

        except (struct.error, UnicodeDecodeError, OSError) as e:
            logger.error("Error handling DNS query from %s: %s", client_ip, e)

    def _parse_question(self, data: bytes, offset: int) -> tuple[Optional[str], int, int]:
        """Parse the question section to extract QNAME and QTYPE.

        Args:
            data: Full DNS packet.
            offset: Starting offset for question section.

        Returns:
            Tuple of (qname, qtype, end_offset) or (None, 0, offset) on failure.
        """
        labels = []
        pos = offset

        while pos < len(data):
            length = data[pos]

            # Check for compression pointer (starts with 0xC0)
            if (length & 0xC0) == 0xC0:
                # Skip compression pointer - we ignore compressed names
                pos += 2
                break

            if length == 0:
                # End of name
                pos += 1
                break

            pos += 1
            if pos + length > len(data):
                return None, 0, offset

            labels.append(data[pos:pos + length].decode('ascii', errors='ignore'))
            pos += length

        if not labels:
            return None, 0, offset

        qname = '.'.join(labels)

        # Read QTYPE (2 bytes, network order)
        if pos + 2 > len(data):
            return qname, 0, pos

        qtype = struct.unpack('!H', data[pos:pos + 2])[0]
        pos += 4  # Skip QTYPE (2) + QCLASS (2)

        return qname, qtype, pos

    def _extract_correlation_id(self, qname: str) -> Optional[str]:
        """Extract correlation ID from the first subdomain label.

        The correlation ID is expected to be the first label of the domain name.
        It must be exactly 16 lowercase hexadecimal characters.

        Args:
            qname: Fully qualified domain name from DNS query.

        Returns:
            The correlation ID if found and valid, None otherwise.
        """
        if not qname:
            return None

        # Get first label (subdomain)
        labels = qname.split('.')
        if not labels:
            return None

        candidate = labels[0]

        # Validate: exactly 16 chars, all lowercase hex
        if len(candidate) != 16:
            return None

        if not all(c in '0123456789abcdef' for c in candidate):
            return None

        return candidate

    def _build_response(
        self,
        txn_id: int,
        query: bytes,
        qname: Optional[str],
        qtype: int
    ) -> bytes:
        """Build a DNS response packet.

        Args:
            txn_id: Transaction ID from query.
            query: Original query packet.
            qname: Query name (for logging).
            qtype: Query type.

        Returns:
            DNS response packet bytes.
        """
        # Response flags: QR=1, OPCODE=0, AA=1, TC=0, RD=1, RA=1, RCODE=0
        # 0x8580 = 1000 0101 1000 0000
        flags = 0x8580

        if qtype == QTYPE_A and qname:
            # Build response with answer
            # Header: ID, FLAGS, QDCOUNT=1, ANCOUNT=1, NSCOUNT=0, ARCOUNT=0
            header = struct.pack('!HHHHHH', txn_id, flags, 1, 1, 0, 0)

            # Copy question section from original query
            question_end = self._find_question_end(query)
            question = query[DNS_HEADER_SIZE:question_end]

            # Answer section: NAME (pointer to question), TYPE, CLASS, TTL, RDLENGTH, RDATA
            # Name pointer: 0xC00C points to offset 12 (start of question)
            answer = struct.pack(
                '!HHHLH4s',
                0xC00C,          # Name pointer
                QTYPE_A,         # TYPE = A
                QCLASS_IN,       # CLASS = IN
                60,              # TTL = 60 seconds
                4,               # RDLENGTH = 4 bytes
                bytes([127, 0, 0, 1])  # RDATA = 127.0.0.1
            )

            return header + question + answer
        else:
            # Return empty answer for non-A queries
            header = struct.pack('!HHHHHH', txn_id, flags, 1, 0, 0, 0)
            question_end = self._find_question_end(query)
            question = query[DNS_HEADER_SIZE:question_end]
            return header + question

    def _find_question_end(self, data: bytes) -> int:
        """Find the end of the question section in a DNS packet.

        Args:
            data: Full DNS packet.

        Returns:
            Offset of the byte after the question section.
        """
        pos = DNS_HEADER_SIZE

        while pos < len(data):
            length = data[pos]

            if (length & 0xC0) == 0xC0:
                pos += 2
                break

            if length == 0:
                pos += 1
                break

            pos += 1 + length

        # Add QTYPE (2) + QCLASS (2)
        return pos + 4


class DNSCallbackServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    """Threading UDP server for capturing DNS callbacks."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        store: 'InjectionStore'
    ):
        """Initialize the DNS callback server.

        Args:
            server_address: Tuple of (host, port) to bind to.
            store: InjectionStore instance for recording callbacks.
        """
        super().__init__(server_address, DNSHandler)
        self.store = store
        self._shutdown_event = threading.Event()

    def serve_until_shutdown(self) -> None:
        """Serve requests until shutdown is requested."""
        while not self._shutdown_event.is_set():
            self.handle_request()

    def request_shutdown(self) -> None:
        """Request the server to stop serving."""
        self._shutdown_event.set()


def run_dns_server(host: str, port: int, store: 'InjectionStore') -> int:
    """Run the DNS callback server until interrupted.

    Args:
        host: Host address to bind to.
        port: Port number to bind to (default: 5353).
        store: InjectionStore instance for recording callbacks.

    Returns:
        Exit code (0 for clean shutdown).
    """
    server = DNSCallbackServer((host, port), store)

    # Set socket timeout for responsive shutdown
    server.socket.settimeout(0.5)

    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        server.request_shutdown()

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"DNS callback server listening on {host}:{port}")
    logger.info("DNS callback server started on %s:%d", host, port)

    try:
        server.serve_until_shutdown()
    finally:
        server.server_close()
        logger.info("DNS callback server stopped")

    return 0
