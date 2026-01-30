"""
Injection orchestrator for multi-vector payload injection.

Coordinates injecting payloads across all identified vectors (query params,
headers, cookies, body fields, JSON) with rate limiting and database tracking.
"""

import json
import re
import secrets
import time
from dataclasses import dataclass, replace
from typing import Optional
from urllib.parse import parse_qsl, urlencode

from ricochet.core.store import InjectionRecord, InjectionStore
from ricochet.injection.http_client import (
    HttpResponse,
    prepare_headers_for_body,
    send_request,
)
from ricochet.injection.parser import ParsedRequest, build_url, inject_into_path
from ricochet.injection.rate_limiter import RateLimiter
from ricochet.injection.vectors import InjectionVector, extract_vectors


@dataclass
class InjectionResult:
    """Result of a single injection attempt."""

    correlation_id: str
    vector: InjectionVector
    url: str
    status: int  # HTTP response status
    success: bool  # Request completed (not timeout/error)
    error: Optional[str]  # Error message if failed


# Pattern to match callback placeholders
CALLBACK_PATTERN = re.compile(
    r'\{\{CALLBACK\}\}|\{\{callback\}\}|\{CALLBACK\}|\$\{CALLBACK\}',
    re.IGNORECASE
)


def substitute_callback(payload: str, callback_url: str, correlation_id: str) -> str:
    """Replace {{CALLBACK}} variants with actual callback URL.

    Supports multiple placeholder formats:
    - {{CALLBACK}}
    - {{callback}}
    - {CALLBACK}
    - ${CALLBACK}

    Args:
        payload: Payload template with callback placeholder
        callback_url: Base callback URL (e.g., http://evil.com)
        correlation_id: Unique ID to append to URL for correlation

    Returns:
        Payload with placeholders replaced by callback_url/correlation_id
    """
    full_url = f"{callback_url.rstrip('/')}/{correlation_id}"
    return CALLBACK_PATTERN.sub(full_url, payload)


def generate_correlation_id() -> str:
    """Generate a unique 16-character hex correlation ID."""
    return secrets.token_hex(8)


class Injector:
    """
    Multi-vector injection orchestrator.

    Manages injecting payloads into all identified vectors of an HTTP request,
    with rate limiting to avoid bans and database tracking for callback
    correlation.
    """

    def __init__(
        self,
        store: InjectionStore,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: float = 10.0,
        callback_url: str = "http://localhost:8080",
    ) -> None:
        """Initialize the injector.

        Args:
            store: InjectionStore for tracking injections
            rate_limiter: Optional rate limiter (default: 10 req/s, burst 1)
            timeout: Request timeout in seconds (default: 10.0)
            callback_url: Base URL for callback server (default: http://localhost:8080)
        """
        self.store = store
        self.rate_limiter = rate_limiter or RateLimiter(rate=10, burst=1)
        self.timeout = timeout
        self.callback_url = callback_url

    def inject_vector(
        self,
        request: ParsedRequest,
        vector: InjectionVector,
        payload: str,
        use_https: bool = False,
        dry_run: bool = False,
    ) -> InjectionResult:
        """Inject payload into a specific vector.

        Args:
            request: Original parsed HTTP request
            vector: Injection vector identifying the target parameter
            payload: Payload template (may contain {{CALLBACK}} placeholder)
            use_https: Use HTTPS instead of HTTP
            dry_run: If True, don't send request, just simulate

        Returns:
            InjectionResult with correlation ID, status, and success indicator
        """
        correlation_id = generate_correlation_id()

        # Substitute callback placeholder with actual URL
        final_payload = substitute_callback(payload, self.callback_url, correlation_id)

        # Build the modified request based on vector type
        modified_request = self._inject_payload(request, vector, final_payload)
        url = build_url(modified_request, use_https=use_https)

        # Record injection in database before sending
        record = InjectionRecord(
            id=correlation_id,
            target_url=url,
            parameter=f"{vector.location}:{vector.name}",
            payload=final_payload,
            timestamp=time.time(),
            context=f"Original value: {vector.original_value}",
        )
        self.store.record_injection(record)

        if dry_run:
            return InjectionResult(
                correlation_id=correlation_id,
                vector=vector,
                url=url,
                status=0,
                success=True,
                error="[dry-run] Request not sent",
            )

        # Rate limit before sending
        self.rate_limiter.acquire()

        # Send the request
        try:
            response = send_request(
                url=url,
                method=modified_request.method,
                headers=prepare_headers_for_body(
                    modified_request.headers, modified_request.body
                ),
                body=modified_request.body,
                timeout=self.timeout,
                verify_ssl=False,  # Common for security testing
                follow_redirects=True,
            )
            return InjectionResult(
                correlation_id=correlation_id,
                vector=vector,
                url=url,
                status=response.status,
                success=True,
                error=None,
            )

        except TimeoutError as e:
            return InjectionResult(
                correlation_id=correlation_id,
                vector=vector,
                url=url,
                status=0,
                success=False,
                error=f"Timeout: {e}",
            )

        except ConnectionError as e:
            return InjectionResult(
                correlation_id=correlation_id,
                vector=vector,
                url=url,
                status=0,
                success=False,
                error=f"Connection error: {e}",
            )

        except Exception as e:
            return InjectionResult(
                correlation_id=correlation_id,
                vector=vector,
                url=url,
                status=0,
                success=False,
                error=f"Unexpected error: {e}",
            )

    def inject_all_vectors(
        self,
        request: ParsedRequest,
        payload: str,
        use_https: bool = False,
        dry_run: bool = False,
    ) -> list[InjectionResult]:
        """Inject payload into all vectors in the request.

        Args:
            request: Original parsed HTTP request
            payload: Payload template
            use_https: Use HTTPS instead of HTTP
            dry_run: If True, don't send requests

        Returns:
            List of InjectionResult for each vector
        """
        vectors = extract_vectors(request)
        results = []

        for vector in vectors:
            result = self.inject_vector(
                request, vector, payload, use_https=use_https, dry_run=dry_run
            )
            results.append(result)

        return results

    def inject_single_param(
        self,
        request: ParsedRequest,
        param_name: str,
        payload: str,
        use_https: bool = False,
        dry_run: bool = False,
    ) -> Optional[InjectionResult]:
        """Inject payload into a specific parameter by name.

        Searches all vector types for a parameter matching the name.

        Args:
            request: Original parsed HTTP request
            param_name: Name of parameter to inject
            payload: Payload template
            use_https: Use HTTPS instead of HTTP
            dry_run: If True, don't send request

        Returns:
            InjectionResult if parameter found, None otherwise
        """
        vectors = extract_vectors(request)

        for vector in vectors:
            if vector.name == param_name:
                return self.inject_vector(
                    request, vector, payload, use_https=use_https, dry_run=dry_run
                )

        return None

    def _inject_payload(
        self, request: ParsedRequest, vector: InjectionVector, payload: str
    ) -> ParsedRequest:
        """Inject payload into the request at the specified vector location.

        Args:
            request: Original request
            vector: Target injection vector
            payload: Payload to inject

        Returns:
            Modified ParsedRequest with payload injected
        """
        if vector.location == "query":
            return inject_into_path(request, vector.name, payload)

        elif vector.location == "header":
            return self._inject_header(request, vector.name, payload)

        elif vector.location == "cookie":
            return self._inject_cookie(request, vector.name, payload)

        elif vector.location == "body":
            return self._inject_form_body(request, vector.name, payload)

        elif vector.location == "json":
            return self._inject_json_body(request, vector.name, payload)

        else:
            # Unknown vector type - return unmodified
            return request

    def _inject_header(
        self, request: ParsedRequest, header_name: str, payload: str
    ) -> ParsedRequest:
        """Inject payload into a header value."""
        new_headers = dict(request.headers)

        # Find and replace header (case-insensitive match)
        for key in list(new_headers.keys()):
            if key.lower() == header_name.lower():
                new_headers[key] = payload
                break

        return replace(request, headers=new_headers)

    def _inject_cookie(
        self, request: ParsedRequest, cookie_name: str, payload: str
    ) -> ParsedRequest:
        """Inject payload into a cookie value."""
        new_headers = dict(request.headers)

        # Find Cookie header
        cookie_key = None
        cookie_value = ""
        for key, value in new_headers.items():
            if key.lower() == "cookie":
                cookie_key = key
                cookie_value = value
                break

        if cookie_key is None:
            return request

        # Parse, modify, and rebuild cookie header
        cookies = []
        for cookie in cookie_value.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                name, val = cookie.split("=", 1)
                if name.strip() == cookie_name:
                    cookies.append(f"{name.strip()}={payload}")
                else:
                    cookies.append(f"{name.strip()}={val}")
            elif cookie:
                cookies.append(cookie)

        new_headers[cookie_key] = "; ".join(cookies)
        return replace(request, headers=new_headers)

    def _inject_form_body(
        self, request: ParsedRequest, param_name: str, payload: str
    ) -> ParsedRequest:
        """Inject payload into form-urlencoded body."""
        if request.body is None:
            return request

        try:
            body_str = request.body.decode("utf-8")
            params = parse_qsl(body_str, keep_blank_values=True)

            new_params = []
            for name, val in params:
                if name == param_name:
                    new_params.append((name, payload))
                else:
                    new_params.append((name, val))

            new_body = urlencode(new_params).encode("utf-8")
            return replace(request, body=new_body)

        except (UnicodeDecodeError, ValueError):
            return request

    def _inject_json_body(
        self, request: ParsedRequest, field_name: str, payload: str
    ) -> ParsedRequest:
        """Inject payload into a JSON body field."""
        if request.body is None:
            return request

        try:
            body_str = request.body.decode("utf-8")
            data = json.loads(body_str)

            if isinstance(data, dict) and field_name in data:
                data[field_name] = payload
                new_body = json.dumps(data).encode("utf-8")
                return replace(request, body=new_body)

            return request

        except (UnicodeDecodeError, json.JSONDecodeError):
            return request
