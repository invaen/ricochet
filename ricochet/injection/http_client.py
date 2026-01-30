"""
HTTP client for injection payload delivery.

Uses stdlib-only urllib.request for sending requests with custom methods,
headers, and bodies. Supports configurable timeouts and SSL verification.
"""

import socket
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class HttpResponse:
    """
    Response from an HTTP request.

    Attributes:
        status: HTTP status code (e.g., 200, 404, 500)
        reason: HTTP reason phrase (e.g., "OK", "Not Found")
        headers: Response headers as dict
        body: Response body as bytes
        url: Final URL after any redirects
    """

    status: int
    reason: str
    headers: dict[str, str]
    body: bytes
    url: str


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Handler that prevents automatic redirect following."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp,
        code: int,
        msg: str,
        headers,
        newurl: str,
    ) -> None:
        """Return None to prevent redirects."""
        return None


def send_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: float = 10.0,
    verify_ssl: bool = True,
    follow_redirects: bool = True,
    proxy_url: Optional[str] = None,
) -> HttpResponse:
    """
    Send an HTTP request with custom method, headers, and body.

    Args:
        url: Target URL (http:// or https://)
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional dict of request headers
        body: Optional request body as bytes
        timeout: Request timeout in seconds (must be > 0)
        verify_ssl: If False, disable SSL certificate verification
        follow_redirects: If False, don't follow 3xx redirects
        proxy_url: Optional HTTP proxy URL (e.g., http://127.0.0.1:8080)

    Returns:
        HttpResponse with status, reason, headers, body, and final URL

    Raises:
        ValueError: If timeout is not positive
        TimeoutError: If request times out
        ConnectionError: If connection fails (DNS, refused, etc.)
    """
    if timeout <= 0:
        raise ValueError(f"timeout must be positive, got {timeout}")

    # Build request
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers or {},
        method=method,
    )

    # Build list of handlers for the opener
    handlers: list = []

    # Proxy handler (must be added before HTTPS handler)
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url,
        })
        handlers.append(proxy_handler)
    else:
        # Disable environment proxy detection when no proxy specified
        handlers.append(urllib.request.ProxyHandler({}))

    # SSL context for unverified connections
    if not verify_ssl:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=context))

    # Optionally disable redirect following
    if not follow_redirects:
        handlers.append(_NoRedirectHandler)

    # Build opener with handlers
    opener = urllib.request.build_opener(*handlers)

    try:
        response = opener.open(req, timeout=timeout)
        return HttpResponse(
            status=response.status,
            reason=response.reason,
            headers=dict(response.headers),
            body=response.read(),
            url=response.url,
        )

    except urllib.error.HTTPError as e:
        # 4xx/5xx errors - still return as HttpResponse
        return HttpResponse(
            status=e.code,
            reason=e.reason,
            headers=dict(e.headers) if e.headers else {},
            body=e.read() if e.fp else b"",
            url=e.url or url,
        )

    except socket.timeout as e:
        raise TimeoutError(f"Request to {url} timed out after {timeout}s") from e

    except urllib.error.URLError as e:
        # Connection errors (DNS failure, refused, etc.)
        if isinstance(e.reason, socket.timeout):
            raise TimeoutError(f"Request to {url} timed out after {timeout}s") from e
        raise ConnectionError(f"Failed to connect to {url}: {e.reason}") from e


def prepare_headers_for_body(
    headers: dict[str, str], body: Optional[bytes]
) -> dict[str, str]:
    """
    Prepare headers for a request body, ensuring Content-Length is correct.

    When injecting payloads into request bodies, the Content-Length header
    must be updated to match the actual body size. This helper ensures
    the header is correctly set.

    Args:
        headers: Original request headers
        body: Request body (or None for bodiless requests)

    Returns:
        New dict with Content-Length set if body is provided

    Example:
        >>> headers = {'User-Agent': 'test'}
        >>> body = b'injected payload'
        >>> prepared = prepare_headers_for_body(headers, body)
        >>> prepared['Content-Length']
        '16'
    """
    result = dict(headers)
    if body is not None:
        result["Content-Length"] = str(len(body))
    return result
