"""Finding dataclass for correlated injection-callback pairs."""

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
