"""SQLite persistence layer for injection tracking."""

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
