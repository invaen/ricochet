"""Finding dataclass for correlated injection-callback pairs."""

import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class Finding:
    """A correlated finding linking an injection to its callback.

    Represents a confirmed vulnerability where an injection triggered
    a callback, proving code execution or data exfiltration occurred.
    """
    correlation_id: str
    target_url: str
    parameter: str
    payload: str
    context: Optional[str]
    injected_at: float
    callback_id: int
    source_ip: str
    request_path: str
    callback_headers: dict
    callback_body: Optional[bytes]
    received_at: float
    delay_seconds: float

    @property
    def severity(self) -> str:
        """Derive severity from vulnerability context.

        Returns:
            'high' for SSTI/SQLi, 'medium' for XSS, 'info' for unknown.
        """
        if self.context is None:
            return 'info'

        ctx_lower = self.context.lower()
        if 'ssti' in ctx_lower:
            return 'high'
        if 'sqli' in ctx_lower:
            return 'high'
        if 'xss' in ctx_lower:
            return 'medium'
        return 'info'

    @property
    def metadata(self) -> Optional[dict]:
        """Extract metadata from callback body if present.

        XSS exfiltration payloads send JSON with captured data.
        Returns dict with url, cookies, dom, ua (user-agent), etc.
        Returns None if body is not valid JSON or not present.
        """
        if not self.callback_body:
            return None
        try:
            data = json.loads(self.callback_body.decode('utf-8'))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass
        return None

    @property
    def has_metadata(self) -> bool:
        """Check if finding has valid JSON metadata from callback."""
        return self.metadata is not None
