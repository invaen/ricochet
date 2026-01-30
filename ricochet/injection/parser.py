"""Burp request file parser for extracting HTTP request components."""

from dataclasses import dataclass, replace
from http.client import parse_headers
from io import BytesIO
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


@dataclass
class ParsedRequest:
    """Represents a parsed HTTP request from a Burp export file."""

    method: str           # GET, POST, etc.
    path: str             # /path?query=value
    http_version: str     # HTTP/1.1
    headers: dict[str, str]
    body: Optional[bytes]
    host: str             # From Host header


def parse_request_file(content: bytes) -> ParsedRequest:
    """Parse a Burp-format request file.

    Args:
        content: Raw HTTP request as bytes (Burp exports use CRLF line endings)

    Returns:
        ParsedRequest with method, path, headers, body, and host extracted

    Raises:
        ValueError: If content is empty or malformed
    """
    if not content or not content.strip():
        raise ValueError("Empty request content")

    # Find header/body boundary
    boundary = b'\r\n\r\n'
    boundary_pos = content.find(boundary)

    if boundary_pos == -1:
        # No body, entire content is headers
        header_section = content
        body = None
    else:
        header_section = content[:boundary_pos]
        body_content = content[boundary_pos + len(boundary):]
        body = body_content if body_content else None

    # Split header section into lines
    lines = header_section.split(b'\r\n')

    if not lines or not lines[0]:
        raise ValueError("Malformed request: missing request line")

    # Parse request line: METHOD PATH HTTP/VERSION
    request_line = lines[0].decode('utf-8', errors='replace')
    parts = request_line.split(' ')

    if len(parts) < 2:
        raise ValueError(f"Malformed request line: {request_line}")

    method = parts[0]
    path = parts[1]

    # Handle missing HTTP version
    if len(parts) >= 3:
        http_version = parts[2]
    else:
        http_version = "HTTP/1.1"

    # Parse headers using http.client.parse_headers
    # Reconstruct header lines for parse_headers (expects lines ending with \r\n)
    header_lines = b'\r\n'.join(lines[1:]) + b'\r\n\r\n'
    headers_dict = {}

    if header_lines.strip():
        parsed = parse_headers(BytesIO(header_lines))
        for key in parsed.keys():
            headers_dict[key] = parsed[key]

    # Extract Host header (case-insensitive)
    host = ""
    for key, value in headers_dict.items():
        if key.lower() == "host":
            host = value
            break

    if not host:
        raise ValueError("Missing Host header")

    return ParsedRequest(
        method=method,
        path=path,
        http_version=http_version,
        headers=headers_dict,
        body=body,
        host=host,
    )


def parse_request_string(content: str) -> ParsedRequest:
    """Parse a request from a string, handling LF or CRLF line endings.

    This is a convenience wrapper that normalizes line endings to CRLF
    before parsing.

    Args:
        content: HTTP request as a string

    Returns:
        ParsedRequest with all fields populated
    """
    # Detect line endings and normalize to CRLF
    # First, normalize all CRLF to LF, then convert all LF to CRLF
    normalized = content.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

    return parse_request_file(normalized.encode('utf-8'))


def build_url(request: ParsedRequest, use_https: bool = False) -> str:
    """Construct a full URL from a ParsedRequest.

    Args:
        request: ParsedRequest with host and path
        use_https: If True, use https:// scheme; otherwise http://

    Returns:
        Full URL string (e.g., "http://example.com:8080/api?id=123")
    """
    scheme = "https" if use_https else "http"
    return f"{scheme}://{request.host}{request.path}"


def inject_into_path(request: ParsedRequest, param: str, value: str) -> ParsedRequest:
    """Replace a query parameter value in the request path.

    Creates a new ParsedRequest with the modified path; does not mutate
    the original request.

    Args:
        request: Original ParsedRequest
        param: Name of the query parameter to replace
        value: New value for the parameter

    Returns:
        New ParsedRequest with the modified path
    """
    parsed_url = urlparse(request.path)

    # Parse existing query params
    params = parse_qsl(parsed_url.query, keep_blank_values=True)

    # Replace the target parameter's value
    new_params = []
    for name, val in params:
        if name == param:
            new_params.append((name, value))
        else:
            new_params.append((name, val))

    # Reconstruct the URL
    new_query = urlencode(new_params)
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment,
    ))

    # Create new ParsedRequest with modified path (using dataclass replace)
    return replace(request, path=new_url)
