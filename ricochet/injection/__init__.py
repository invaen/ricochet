"""
Injection engine for Ricochet.

Provides HTTP request parsing, injection vector extraction, and rate limiting
infrastructure for controlled injection payload delivery.
"""

from ricochet.injection.http_client import HttpResponse, send_request
from ricochet.injection.parser import ParsedRequest, parse_request_file, parse_request_string
from ricochet.injection.rate_limiter import RateLimiter
from ricochet.injection.vectors import InjectionVector, extract_vectors

__all__ = [
    "HttpResponse",
    "InjectionVector",
    "ParsedRequest",
    "RateLimiter",
    "extract_vectors",
    "parse_request_file",
    "parse_request_string",
    "send_request",
]
