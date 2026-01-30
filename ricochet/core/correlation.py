"""Correlation ID generation for tracking injections across contexts."""

import secrets


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for injection tracking.

    Returns:
        A 16-character hexadecimal string (0-9, a-f).

    The ID format is designed to:
    - Survive truncation in most contexts (16 chars is short)
    - Avoid collisions (16^16 = 18 quintillion possibilities)
    - Be URL-safe without encoding (hex chars only)
    - Work in headers, cookies, query params, and payloads
    """
    return secrets.token_hex(8)
