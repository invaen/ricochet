"""Interactsh client for external callback infrastructure.

This module provides a minimal Interactsh client for generating callback URLs
and polling for interactions from self-hosted Interactsh servers.

IMPORTANT LIMITATIONS:
- Public Interactsh servers (oast.pro, oast.fun, etc.) require RSA+AES encryption
  for the poll endpoint. This implementation does NOT support encryption due to
  ricochet's zero-dependency constraint.
- This client works with self-hosted Interactsh servers that have encryption
  disabled (--no-encryption flag on server).
- For public servers, use this module for subdomain/URL generation only, then
  poll using the official interactsh-client or external tooling.

Typical workflow with public servers:
1. Generate correlation ID and callback URLs using this module
2. Inject payloads with the generated URLs
3. Poll for callbacks using: interactsh-client -server oast.pro -token <secret>
4. Manually correlate callbacks or use external tooling
"""

import json
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ricochet.core.store import InjectionStore


@dataclass
class InteractshInteraction:
    """Record of an interaction received by Interactsh server."""
    protocol: str  # dns, http, smtp, etc.
    unique_id: str  # Correlation ID portion
    full_id: str  # Full subdomain
    raw_request: str  # Request data
    remote_address: str  # Source IP
    timestamp: str  # ISO format


class InteractshClient:
    """Client for interacting with Interactsh callback infrastructure.

    This client generates callback URLs and polls for interactions.
    Note: Polling only works with self-hosted servers that have encryption
    disabled. Public servers require RSA+AES encryption not implemented here.
    """

    def __init__(
        self,
        server: str,
        correlation_id: str,
        secret: str | None = None
    ):
        """Initialize Interactsh client.

        Args:
            server: Interactsh server hostname (e.g., "oast.pro")
            correlation_id: 16-char hex ID from ricochet
            secret: Optional secret for authenticated polling
        """
        self.server = server.lower().strip()
        self.correlation_id = correlation_id.lower()
        self.secret = secret

    @property
    def subdomain(self) -> str:
        """Return subdomain for callback URLs.

        Format: {correlation_id}.{server}
        """
        return f"{self.correlation_id}.{self.server}"

    @property
    def base_url(self) -> str:
        """Return base URL for API calls."""
        return f"https://{self.server}"

    def generate_url(self, protocol: str = "http") -> str:
        """Generate a callback URL for the given protocol.

        Args:
            protocol: Protocol type - "http" or "dns"

        Returns:
            Callback URL or subdomain for the protocol.
        """
        if protocol.lower() == "dns":
            return self.subdomain
        return f"http://{self.subdomain}/callback"

    def poll(
        self,
        store: 'InjectionStore | None' = None
    ) -> list[InteractshInteraction]:
        """Poll Interactsh server for interactions.

        IMPORTANT: This will FAIL on public servers that require encryption.
        Only works with self-hosted servers using --no-encryption flag.

        Args:
            store: Optional InjectionStore to record callbacks.

        Returns:
            List of InteractshInteraction objects. Empty list on error.
        """
        url = f"{self.base_url}/poll?id={self.correlation_id}"
        if self.secret:
            url += f"&secret={self.secret}"

        try:
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'ricochet')

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError:
            # Expected failure on public servers due to encryption requirement
            return []
        except (json.JSONDecodeError, TimeoutError):
            return []

        interactions = []
        raw_data = data.get('data', []) or []

        for item in raw_data:
            interaction = InteractshInteraction(
                protocol=item.get('protocol', 'unknown'),
                unique_id=item.get('unique-id', ''),
                full_id=item.get('full-id', ''),
                raw_request=item.get('raw-request', ''),
                remote_address=item.get('remote-address', ''),
                timestamp=item.get('timestamp', datetime.now(timezone.utc).isoformat())
            )
            interactions.append(interaction)

            # Record callback in store if provided
            if store is not None:
                store.record_callback(
                    correlation_id=self.correlation_id,
                    source_ip=interaction.remote_address,
                    request_path=f"/{interaction.protocol}/{interaction.full_id}",
                    headers={'X-Interactsh-Protocol': interaction.protocol},
                    body=interaction.raw_request.encode() if interaction.raw_request else None
                )

        return interactions


def create_interactsh_client(
    store: 'InjectionStore | None' = None,
    server: str = "oast.pro"
) -> InteractshClient:
    """Create an Interactsh client with a new correlation ID.

    Args:
        store: Optional InjectionStore (unused, kept for API compatibility).
        server: Interactsh server hostname.

    Returns:
        Configured InteractshClient with a fresh correlation ID.
    """
    correlation_id = secrets.token_hex(8)  # 16-char hex
    return InteractshClient(server=server, correlation_id=correlation_id)
