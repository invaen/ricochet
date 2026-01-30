"""
Injection engine for Ricochet.

Provides HTTP request parsing, injection vector extraction, and rate limiting
infrastructure for controlled injection payload delivery.
"""

from ricochet.injection.http_client import HttpResponse, prepare_headers_for_body, send_request
from ricochet.injection.injector import InjectionResult, Injector, substitute_callback
from ricochet.injection.parser import (
    ParsedRequest,
    build_url,
    inject_into_path,
    parse_request_file,
    parse_request_string,
)
from ricochet.injection.rate_limiter import RateLimiter
from ricochet.injection.vectors import InjectionVector, extract_vectors

__all__ = [
    "HttpResponse",
    "InjectionResult",
    "InjectionVector",
    "Injector",
    "ParsedRequest",
    "RateLimiter",
    "build_url",
    "extract_vectors",
    "inject_into_path",
    "parse_request_file",
    "parse_request_string",
    "prepare_headers_for_body",
    "send_request",
    "substitute_callback",
]
