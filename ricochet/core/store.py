"""SQLite persistence layer for injection tracking."""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    """Get the default database path, creating parent directory if needed.

    Returns:
        Path to ~/.ricochet/ricochet.db
    """
    db_dir = Path.home() / '.ricochet'
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / 'ricochet.db'


@dataclass
class InjectionRecord:
    """Record of an injection attempt for tracking callbacks."""
    id: str  # Correlation ID
    target_url: str
    parameter: str
    payload: str
    timestamp: float
    context: Optional[str] = None


@dataclass
class CallbackRecord:
    """Record of a received callback."""
    id: int
    correlation_id: str
    source_ip: str
    request_path: str
    headers: dict
    body: Optional[bytes]
    received_at: float


class InjectionStore:
    """SQLite-based storage for injection records and callbacks."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the store with optional custom database path.

        Args:
            db_path: Path to database file. Defaults to ~/.ricochet/ricochet.db
        """
        self.db_path = db_path if db_path is not None else get_db_path()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a database connection with proper settings.

        Returns:
            Configured SQLite connection with foreign keys enabled.
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema if not exists."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS injections (
                    id TEXT PRIMARY KEY,
                    target_url TEXT NOT NULL,
                    parameter TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    context TEXT,
                    injected_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS callbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT NOT NULL,
                    source_ip TEXT,
                    request_path TEXT,
                    headers TEXT,
                    body TEXT,
                    received_at REAL NOT NULL,
                    FOREIGN KEY (correlation_id) REFERENCES injections(id)
                );

                CREATE INDEX IF NOT EXISTS idx_callbacks_correlation
                ON callbacks(correlation_id);

                CREATE INDEX IF NOT EXISTS idx_injections_timestamp
                ON injections(injected_at);
            """)

    def record_injection(self, record: InjectionRecord) -> None:
        """Store an injection record.

        Args:
            record: InjectionRecord to persist.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO injections (id, target_url, parameter, payload, context, injected_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (record.id, record.target_url, record.parameter,
                 record.payload, record.context, record.timestamp)
            )

    def get_injection(self, correlation_id: str) -> Optional[InjectionRecord]:
        """Retrieve an injection record by correlation ID.

        Args:
            correlation_id: The unique identifier for the injection.

        Returns:
            InjectionRecord if found, None otherwise.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM injections WHERE id = ?",
                (correlation_id,)
            ).fetchone()

        if row is None:
            return None

        return InjectionRecord(
            id=row['id'],
            target_url=row['target_url'],
            parameter=row['parameter'],
            payload=row['payload'],
            timestamp=row['injected_at'],
            context=row['context']
        )

    def list_injections(self, limit: int = 100) -> list[InjectionRecord]:
        """List recent injection records.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of InjectionRecords ordered by timestamp (newest first).
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM injections ORDER BY injected_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

        return [
            InjectionRecord(
                id=row['id'],
                target_url=row['target_url'],
                parameter=row['parameter'],
                payload=row['payload'],
                timestamp=row['injected_at'],
                context=row['context']
            )
            for row in rows
        ]

    def record_callback(
        self,
        correlation_id: str,
        source_ip: str,
        request_path: str,
        headers: dict,
        body: Optional[bytes]
    ) -> bool:
        """Store a callback record.

        Args:
            correlation_id: The correlation ID from the callback URL.
            source_ip: IP address of the callback source.
            request_path: Full request path including query string.
            headers: Request headers as a dictionary.
            body: Request body bytes, or None.

        Returns:
            True if callback was recorded (correlation ID exists),
            False if correlation ID is unknown.
        """
        with self._get_connection() as conn:
            # Check if the injection exists (foreign key constraint)
            exists = conn.execute(
                "SELECT 1 FROM injections WHERE id = ?",
                (correlation_id,)
            ).fetchone()

            if exists is None:
                return False

            conn.execute(
                """
                INSERT INTO callbacks
                (correlation_id, source_ip, request_path, headers, body, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    correlation_id,
                    source_ip,
                    request_path,
                    json.dumps(headers),
                    body,
                    time.time()
                )
            )
            return True

    def get_callbacks_for_injection(self, correlation_id: str) -> list[CallbackRecord]:
        """Get all callbacks for a specific injection.

        Args:
            correlation_id: The correlation ID to query.

        Returns:
            List of CallbackRecords ordered by received_at (newest first).
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM callbacks
                WHERE correlation_id = ?
                ORDER BY received_at DESC
                """,
                (correlation_id,)
            ).fetchall()

        return [
            CallbackRecord(
                id=row['id'],
                correlation_id=row['correlation_id'],
                source_ip=row['source_ip'],
                request_path=row['request_path'],
                headers=json.loads(row['headers']) if row['headers'] else {},
                body=row['body'].encode() if isinstance(row['body'], str) else row['body'],
                received_at=row['received_at']
            )
            for row in rows
        ]

    def get_injections_with_callbacks(self) -> list[tuple[InjectionRecord, int]]:
        """Get all injections that have received callbacks.

        Returns:
            List of tuples (InjectionRecord, callback_count) ordered by
            most recent callback first.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT i.*, COUNT(c.id) as callback_count,
                       MAX(c.received_at) as last_callback
                FROM injections i
                JOIN callbacks c ON i.id = c.correlation_id
                GROUP BY i.id
                ORDER BY last_callback DESC
                """
            ).fetchall()

        return [
            (
                InjectionRecord(
                    id=row['id'],
                    target_url=row['target_url'],
                    parameter=row['parameter'],
                    payload=row['payload'],
                    timestamp=row['injected_at'],
                    context=row['context']
                ),
                row['callback_count']
            )
            for row in rows
        ]
