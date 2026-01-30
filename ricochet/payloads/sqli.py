"""
SQLi OOB payload generator for blind SQL injection detection.

Generates SQL injection payloads that trigger out-of-band callbacks via
database-specific features. These payloads work for blind SQLi where no
in-band error messages are visible - the callback proves code execution
on the database server.

Supported databases:
    - MSSQL: xp_dirtree, xp_fileexist (UNC paths)
    - MySQL: LOAD_FILE (UNC paths)
    - Oracle: UTL_HTTP, UTL_INADDR, DBMS_LDAP
    - PostgreSQL: dblink, COPY TO PROGRAM
"""

from pathlib import Path
from typing import Iterator, Optional

# Import directly to avoid loading full injection module chain
from ricochet.injection.payloads import load_payloads  # noqa: E402


class SQLiPayloadGenerator:
    """Generate SQL injection out-of-band payloads for blind SQLi detection.

    Payloads use database-specific techniques to trigger DNS or HTTP callbacks
    from the database server. A callback proves code execution occurred.

    Attributes:
        vuln_type: The vulnerability type identifier ("sqli")
        DATABASES: List of supported database types

    Example:
        >>> gen = SQLiPayloadGenerator()  # All databases
        >>> for payload, db in gen.generate("callback.example.com"):
        ...     print(f"[{db}] {payload}")

        >>> gen = SQLiPayloadGenerator("mssql")  # MSSQL only
        >>> for payload, db in gen.generate("callback.example.com"):
        ...     print(payload)
    """

    vuln_type = "sqli"
    DATABASES = ["mssql", "mysql", "oracle", "postgres"]

    def __init__(self, database: Optional[str] = None):
        """Initialize the SQLi payload generator.

        Args:
            database: Specific database to target (mssql, mysql, oracle, postgres).
                     If None, generates payloads for all databases.

        Raises:
            ValueError: If database is specified but not in DATABASES list.
        """
        if database is not None and database not in self.DATABASES:
            raise ValueError(
                f"Unknown database '{database}'. "
                f"Supported: {', '.join(self.DATABASES)}"
            )
        self.database = database

    def generate(self, callback_url: str) -> Iterator[tuple[str, str]]:
        """Generate SQLi OOB payloads with callback URL substituted.

        Yields payloads with {{CALLBACK}} placeholder replaced by the
        provided callback URL.

        Args:
            callback_url: The callback URL/domain to substitute into payloads.
                         This should be a DNS-resolvable domain you control.

        Yields:
            Tuples of (payload, database) where payload has {{CALLBACK}}
            replaced with callback_url.

        Example:
            >>> gen = SQLiPayloadGenerator()
            >>> payloads = list(gen.generate("test.callback.com"))
            >>> len(payloads) >= 8  # At least 2 per database
            True
        """
        builtin_dir = Path(__file__).parent / "builtin"

        databases = [self.database] if self.database else self.DATABASES

        for db in databases:
            filepath = builtin_dir / f"sqli-dns-{db}.txt"
            if filepath.exists():
                for payload in load_payloads(filepath):
                    # Substitute callback placeholder
                    substituted = payload.replace("{{CALLBACK}}", callback_url)
                    yield (substituted, db)
