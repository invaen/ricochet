"""HTTP callback server for capturing OOB interactions."""

import logging
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from ricochet.core.store import InjectionStore

logger = logging.getLogger(__name__)


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler that captures callbacks and extracts correlation IDs."""

    server: 'CallbackServer'  # Type hint for the server reference

    def log_message(self, format: str, *args) -> None:
        """Override to use logging module instead of stderr."""
        logger.debug("%s - %s", self.address_string(), format % args)

    def _extract_correlation_id(self) -> str | None:
        """Extract correlation ID from the URL path.

        The correlation ID is expected to be the last non-empty segment
        of the URL path. It must be exactly 16 hexadecimal characters.

        Returns:
            The correlation ID if found and valid, None otherwise.
        """
        parsed = urlparse(self.path)
        segments = [s for s in parsed.path.split('/') if s]

        if not segments:
            return None

        candidate = segments[-1]

        # Validate: exactly 16 chars, all lowercase hex
        if len(candidate) != 16:
            return None

        if not all(c in '0123456789abcdef' for c in candidate):
            return None

        return candidate

    def _handle_callback(self, body: bytes | None = None) -> None:
        """Process an incoming callback request.

        Extracts correlation ID, records the callback if ID is known,
        and always returns 200 OK to avoid leaking valid/invalid IDs.

        Args:
            body: Request body bytes for POST/PUT requests, None for others.
        """
        correlation_id = self._extract_correlation_id()
        source_ip = self.client_address[0]

        if correlation_id:
            # Convert headers to dict
            headers = dict(self.headers.items())

            recorded = self.server.store.record_callback(
                correlation_id=correlation_id,
                source_ip=source_ip,
                request_path=self.path,
                headers=headers,
                body=body
            )

            if recorded:
                logger.info(
                    "Callback received: correlation_id=%s source=%s path=%s",
                    correlation_id, source_ip, self.path
                )
            else:
                logger.warning(
                    "Unknown correlation ID: %s from %s",
                    correlation_id, source_ip
                )
        else:
            logger.debug(
                "Request without correlation ID from %s: %s",
                source_ip, self.path
            )

        # Always return 200 OK to avoid leaking information
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'OK')

    def _read_body(self) -> bytes | None:
        """Read request body based on Content-Length header."""
        content_length = self.headers.get('Content-Length')
        if content_length:
            try:
                length = int(content_length)
                return self.rfile.read(length)
            except (ValueError, IOError):
                return None
        return None

    def do_GET(self) -> None:
        """Handle GET requests."""
        self._handle_callback()

    def do_POST(self) -> None:
        """Handle POST requests."""
        body = self._read_body()
        self._handle_callback(body)

    def do_HEAD(self) -> None:
        """Handle HEAD requests."""
        self._handle_callback()

    def do_PUT(self) -> None:
        """Handle PUT requests."""
        body = self._read_body()
        self._handle_callback(body)

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        self._handle_callback()

    def do_OPTIONS(self) -> None:
        """Handle OPTIONS requests."""
        self._handle_callback()

    def do_PATCH(self) -> None:
        """Handle PATCH requests."""
        body = self._read_body()
        self._handle_callback(body)


class CallbackServer(ThreadingHTTPServer):
    """Threading HTTP server for capturing callbacks."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        store: 'InjectionStore'
    ):
        """Initialize the callback server.

        Args:
            server_address: Tuple of (host, port) to bind to.
            store: InjectionStore instance for recording callbacks.
        """
        super().__init__(server_address, CallbackHandler)
        self.store = store
        self.timeout = 0.5  # For responsive shutdown
        self._shutdown_event = threading.Event()

    def serve_until_shutdown(self) -> None:
        """Serve requests until shutdown is requested."""
        while not self._shutdown_event.is_set():
            self.handle_request()

    def request_shutdown(self) -> None:
        """Request the server to stop serving."""
        self._shutdown_event.set()


def run_callback_server(host: str, port: int, store: 'InjectionStore') -> int:
    """Run the callback server until interrupted.

    Args:
        host: Host address to bind to.
        port: Port number to bind to.
        store: InjectionStore instance for recording callbacks.

    Returns:
        Exit code (0 for clean shutdown).
    """
    server = CallbackServer((host, port), store)

    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        server.request_shutdown()

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"Callback server listening on {host}:{port}")
    logger.info("Callback server started on %s:%d", host, port)

    try:
        server.serve_until_shutdown()
    finally:
        server.server_close()
        logger.info("Callback server stopped")

    return 0
