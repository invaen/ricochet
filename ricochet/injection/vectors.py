"""Injection vector extraction from parsed HTTP requests."""

import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl, urlparse

from ricochet.injection.parser import ParsedRequest


# Headers commonly used in security testing that may be injectable
INJECTABLE_HEADERS = {
    'User-Agent',
    'Referer',
    'X-Forwarded-For',
    'X-Forwarded-Host',
    'X-Custom-IP-Authorization',
    'X-Original-URL',
    'X-Rewrite-URL',
    'X-Client-IP',
    'True-Client-IP',
    'Forwarded',
    'Origin',
}


@dataclass
class InjectionVector:
    """Represents a single injectable parameter location."""

    location: Literal['query', 'header', 'cookie', 'body', 'json']
    name: str
    original_value: str


def extract_vectors(request: ParsedRequest) -> list[InjectionVector]:
    """Extract all injectable parameters from a parsed request.

    Identifies potential injection points in:
    - Query string parameters
    - Security-relevant HTTP headers
    - Cookies
    - Form body fields (application/x-www-form-urlencoded)
    - JSON body fields (application/json, top-level strings only)

    Args:
        request: ParsedRequest from parse_request_file

    Returns:
        List of InjectionVector objects representing each injectable parameter
    """
    vectors: list[InjectionVector] = []

    # Extract query parameters
    vectors.extend(_extract_query_params(request))

    # Extract injectable headers
    vectors.extend(_extract_headers(request))

    # Extract cookies
    vectors.extend(_extract_cookies(request))

    # Extract body parameters (form or JSON)
    vectors.extend(_extract_body(request))

    return vectors


def _extract_query_params(request: ParsedRequest) -> list[InjectionVector]:
    """Extract query string parameters from the request path."""
    vectors: list[InjectionVector] = []

    parsed_url = urlparse(request.path)
    if parsed_url.query:
        params = parse_qsl(parsed_url.query, keep_blank_values=True)
        for name, value in params:
            vectors.append(InjectionVector(
                location='query',
                name=name,
                original_value=value,
            ))

    return vectors


def _extract_headers(request: ParsedRequest) -> list[InjectionVector]:
    """Extract security-relevant headers that may be injectable."""
    vectors: list[InjectionVector] = []

    for header_name, header_value in request.headers.items():
        # Check if this header is in our injectable list (case-insensitive)
        for injectable in INJECTABLE_HEADERS:
            if header_name.lower() == injectable.lower():
                vectors.append(InjectionVector(
                    location='header',
                    name=header_name,
                    original_value=header_value,
                ))
                break

    return vectors


def _extract_cookies(request: ParsedRequest) -> list[InjectionVector]:
    """Extract cookies from the Cookie header."""
    vectors: list[InjectionVector] = []

    # Find Cookie header (case-insensitive)
    cookie_header = None
    for key, value in request.headers.items():
        if key.lower() == 'cookie':
            cookie_header = value
            break

    if cookie_header:
        # Parse cookies: "name1=value1; name2=value2"
        cookies = cookie_header.split(';')
        for cookie in cookies:
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                vectors.append(InjectionVector(
                    location='cookie',
                    name=name.strip(),
                    original_value=value.strip(),
                ))

    return vectors


def _extract_body(request: ParsedRequest) -> list[InjectionVector]:
    """Extract body parameters (form-urlencoded or JSON)."""
    vectors: list[InjectionVector] = []

    if not request.body:
        return vectors

    # Get Content-Type header (case-insensitive)
    content_type = ""
    for key, value in request.headers.items():
        if key.lower() == 'content-type':
            content_type = value.lower()
            break

    if 'application/x-www-form-urlencoded' in content_type:
        # Parse form body
        try:
            body_str = request.body.decode('utf-8')
            params = parse_qsl(body_str, keep_blank_values=True)
            for name, value in params:
                vectors.append(InjectionVector(
                    location='body',
                    name=name,
                    original_value=value,
                ))
        except (UnicodeDecodeError, ValueError):
            pass  # Skip malformed bodies

    elif 'application/json' in content_type:
        # Parse JSON body, extract top-level string fields only
        try:
            body_str = request.body.decode('utf-8')
            data = json.loads(body_str)
            if isinstance(data, dict):
                for key, value in data.items():
                    # Only extract string values (recursive is future work)
                    if isinstance(value, str):
                        vectors.append(InjectionVector(
                            location='json',
                            name=key,
                            original_value=value,
                        ))
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass  # Skip malformed JSON

    return vectors
