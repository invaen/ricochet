"""
Injection engine for Ricochet.

Provides HTTP client and rate limiting infrastructure for controlled
injection payload delivery.
"""

from ricochet.injection.rate_limiter import RateLimiter

__all__ = ["RateLimiter"]
