"""Burp request file parser for extracting HTTP request components."""

from dataclasses import dataclass
from http.client import parse_headers
from io import BytesIO
from typing import Optional


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
