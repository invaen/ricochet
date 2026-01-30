# Phase 1: Foundation - Research

**Researched:** 2026-01-29
**Domain:** Python CLI architecture, SQLite persistence, zero-dependency design
**Confidence:** HIGH

## Summary

Phase 1 establishes the zero-dependency CLI architecture with persistent storage for injection tracking. This phase focuses on four core areas: (1) argparse-based CLI with subcommands following Unix conventions, (2) SQLite schema for injection/callback correlation, (3) project structure optimized for a stdlib-only Python CLI tool, and (4) CLI UX best practices including help, version, and exit codes.

The standard approach for a zero-dependency Python CLI tool is to use `argparse` for command parsing with subcommands, `sqlite3` for persistence (it's in stdlib), and a flat package layout with `__main__.py` for the entry point. The CLI should follow Unix conventions: exit code 0 for success, 1 for runtime errors, 2 for argument errors.

**Primary recommendation:** Use argparse with `add_subparsers()` for CLI structure, SQLite with foreign keys for data persistence (PRAGMA foreign_keys must be enabled explicitly), and a simple package layout with `ricochet/__main__.py` as the entry point.

## Standard Stack

The established libraries/tools for this domain (all Python stdlib):

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib | CLI argument parsing, subcommands | Industry standard for Python CLIs; zero dependencies; supports subcommands, help generation, type validation |
| `sqlite3` | stdlib | Persistent storage for injections/callbacks | ACID-compliant, built into Python, supports concurrent reads, efficient for correlation queries |
| `logging` | stdlib | Structured output, debug levels | Built-in formatters, handlers, log levels; essential for security tooling |
| `pathlib` | stdlib | Cross-platform path handling | Modern path handling, works on all platforms |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` | stdlib | Config files, export format | Human-readable output, state serialization |
| `configparser` | stdlib | INI-style config files | User-editable configuration (optional) |
| `dataclasses` | stdlib (3.7+) | Data structures | Clean model definitions for InjectionRecord, CallbackRecord |
| `typing` | stdlib | Type hints | Self-documenting code, IDE support |
| `secrets` | stdlib | Secure random generation | Cryptographically secure correlation IDs |
| `uuid` | stdlib | Unique identifiers | Alternative to secrets for correlation IDs |
| `hashlib` | stdlib | Hashing | Content deduplication, ID generation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | click/typer | Click/Typer have better ergonomics but are external dependencies |
| sqlite3 | JSON files | JSON simpler but lacks query capability and ACID guarantees |
| dataclasses | NamedTuple | NamedTuple is immutable; dataclasses allow defaults and mutability |
| configparser | tomllib (3.11+) | TOML is more modern but requires Python 3.11+ |

**Installation:**
```bash
# No installation needed - stdlib only
python3 --version  # Verify 3.9+
```

## Architecture Patterns

### Recommended Project Structure

```
ricochet/
├── __init__.py           # Package marker, version info
├── __main__.py           # Entry point: python -m ricochet
├── cli.py                # argparse setup, subcommand dispatch
├── config.py             # Configuration dataclasses
├── core/
│   ├── __init__.py
│   ├── store.py          # SQLite persistence layer
│   └── correlation.py    # ID generation, matching logic
└── utils/
    ├── __init__.py
    └── logging.py        # Logging configuration
```

**Rationale:**
- Flat layout (no `src/`) is simpler for a CLI tool that doesn't need installation separation
- `__main__.py` enables `python -m ricochet` execution
- `cli.py` separates argument parsing from business logic
- `core/store.py` isolates database operations for testability

### Pattern 1: Argparse with Subcommands

**What:** Use `add_subparsers()` with `set_defaults(func=handler)` to dispatch subcommands to handler functions.

**When to use:** Always for CLI tools with multiple distinct operations (inject, listen, correlate, report).

**Example:**
```python
# Source: https://docs.python.org/3/library/argparse.html
import argparse
import sys

def cmd_inject(args):
    """Handle inject subcommand."""
    print(f"Injecting into {args.target}")
    return 0

def cmd_listen(args):
    """Handle listen subcommand."""
    print(f"Listening on port {args.port}")
    return 0

def create_parser():
    parser = argparse.ArgumentParser(
        prog='ricochet',
        description='Second-order vulnerability detection tool',
        epilog='For more info: https://github.com/user/ricochet'
    )
    parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase verbosity (-v, -vv, -vvv)')

    subparsers = parser.add_subparsers(
        title='commands',
        description='Available commands',
        dest='command',
        required=True
    )

    # inject subcommand
    inject_parser = subparsers.add_parser('inject', help='Inject payloads into target')
    inject_parser.add_argument('target', help='Target URL')
    inject_parser.set_defaults(func=cmd_inject)

    # listen subcommand
    listen_parser = subparsers.add_parser('listen', help='Start callback server')
    listen_parser.add_argument('-p', '--port', type=int, default=8080,
                               help='Port to listen on (default: 8080)')
    listen_parser.set_defaults(func=cmd_listen)

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    # Dispatch to subcommand handler
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
```

### Pattern 2: SQLite Store with Context Manager

**What:** Wrap SQLite operations in a Store class that uses context managers for transactions and enables foreign keys on connect.

**When to use:** Always for database operations to ensure proper transaction handling and cleanup.

**Example:**
```python
# Source: https://docs.python.org/3/library/sqlite3.html
import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

@dataclass
class InjectionRecord:
    id: str
    target_url: str
    parameter: str
    payload: str
    timestamp: float
    context: Optional[str] = None

class InjectionStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript('''
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
            ''')

    def record_injection(self, record: InjectionRecord) -> None:
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO injections (id, target_url, parameter, payload, context, injected_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (record.id, record.target_url, record.parameter,
                  record.payload, record.context, record.timestamp))

    def get_injection(self, correlation_id: str) -> Optional[InjectionRecord]:
        with self._get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM injections WHERE id = ?',
                (correlation_id,)
            ).fetchone()
            if row:
                return InjectionRecord(
                    id=row['id'],
                    target_url=row['target_url'],
                    parameter=row['parameter'],
                    payload=row['payload'],
                    context=row['context'],
                    timestamp=row['injected_at']
                )
            return None
```

### Pattern 3: Entry Point with __main__.py

**What:** Minimal `__main__.py` that imports and calls the CLI main function.

**When to use:** Always - enables `python -m ricochet` execution.

**Example:**
```python
# ricochet/__main__.py
# Source: https://docs.python.org/3/library/__main__.html
from ricochet.cli import main
import sys

sys.exit(main())
```

**Note:** Keep `__main__.py` minimal. The main logic should be in `cli.py` for testability.

### Pattern 4: Unix Exit Code Conventions

**What:** Use standard exit codes: 0 for success, 1 for runtime errors, 2 for argument errors.

**When to use:** Always for CLI tools to enable scripting and automation.

**Example:**
```python
# Source: https://docs.python.org/3/library/argparse.html + Unix conventions
import sys

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1        # Runtime/application error
EXIT_USAGE = 2        # Command line usage error (argparse default)

def main():
    try:
        parser = create_parser()
        args = parser.parse_args()  # Exits with code 2 on error
        result = args.func(args)
        return EXIT_SUCCESS if result is None else result
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130  # 128 + SIGINT(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_ERROR
```

### Anti-Patterns to Avoid

- **Global database connections:** Don't create a single global connection. Use connection per operation with context managers.
- **Monolithic cli.py:** Don't put all business logic in cli.py. It should only parse args and dispatch to handlers.
- **Raw sys.argv parsing:** Don't parse sys.argv manually. Use argparse for consistency and help generation.
- **Catching SystemExit from argparse:** Don't catch SystemExit to change exit codes. Override `ArgumentParser.error()` if needed.
- **Hardcoded paths:** Don't hardcode database paths. Use `~/.ricochet/` or XDG base directories.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | Manual sys.argv parsing | `argparse` | Help generation, type validation, subcommands |
| Database schema | Raw SQL strings everywhere | Single schema init function | Consistency, versioning, migrations |
| Configuration paths | Hardcoded strings | `pathlib.Path.home() / '.ricochet'` | Cross-platform, expandable |
| ID generation | `random.choice()` | `secrets.token_hex(8)` | Cryptographically secure, prevents enumeration |
| JSON in SQLite | Manual serialization | `json.dumps()`/`json.loads()` | Handles encoding edge cases |

**Key insight:** Python stdlib covers all needs for Phase 1. The temptation is to build "simple" utilities, but stdlib versions handle edge cases (Unicode, platform differences, thread safety) that manual implementations miss.

## Common Pitfalls

### Pitfall 1: Foreign Keys Disabled by Default

**What goes wrong:** SQLite foreign key constraints are ignored because they're disabled by default.

**Why it happens:** SQLite maintains backward compatibility with older versions that didn't support foreign keys.

**How to avoid:** Execute `PRAGMA foreign_keys = ON` after every connection.

**Warning signs:** Deleting parent records doesn't cascade, orphan records accumulate.

### Pitfall 2: Database Path Not Created

**What goes wrong:** First run fails with "unable to open database file" because parent directory doesn't exist.

**Why it happens:** `sqlite3.connect()` creates the file but not parent directories.

**How to avoid:** Use `Path.mkdir(parents=True, exist_ok=True)` before connecting.

**Warning signs:** FileNotFoundError on first run, works on second run if user creates directory manually.

### Pitfall 3: Argparse Exits on Error by Default

**What goes wrong:** Invalid arguments cause immediate exit with no chance for custom error handling.

**Why it happens:** argparse calls `sys.exit(2)` on parse errors by default.

**How to avoid:** If custom handling needed, subclass ArgumentParser and override `error()` method. For most cases, default behavior is correct.

**Warning signs:** Stack traces from argparse instead of clean error messages.

### Pitfall 4: Version String Not in Sync

**What goes wrong:** `--version` shows different version than package metadata or pyproject.toml.

**Why it happens:** Version defined in multiple places (cli.py, __init__.py, pyproject.toml).

**How to avoid:** Define version once in `__init__.py` as `__version__`, import it everywhere.

```python
# ricochet/__init__.py
__version__ = "0.1.0"

# ricochet/cli.py
from ricochet import __version__
parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
```

### Pitfall 5: Correlation ID Truncation

**What goes wrong:** Target application truncates or sanitizes the correlation ID, breaking callback-to-injection matching.

**Why it happens:** IDs too long for database fields, special characters stripped, URL encoding issues.

**How to avoid:**
- Keep IDs short (12-16 alphanumeric characters)
- Use only alphanumeric characters (no hyphens, underscores in the ID portion)
- Verify ID survives round-trip in test payloads

**Warning signs:** Callbacks arrive but correlation_id is truncated or empty.

## Code Examples

Verified patterns from official sources:

### Database Initialization

```python
# Source: https://docs.python.org/3/library/sqlite3.html
import sqlite3
from pathlib import Path

def get_db_path() -> Path:
    """Get database path, creating directory if needed."""
    db_dir = Path.home() / '.ricochet'
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / 'ricochet.db'

def init_database(db_path: Path) -> None:
    """Initialize database schema."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript('''
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
    ''')
    conn.commit()
    conn.close()
```

### CLI Entry Point

```python
# Source: https://docs.python.org/3/library/argparse.html
#!/usr/bin/env python3
"""Ricochet - Second-order vulnerability detection tool."""

import argparse
import sys
from pathlib import Path

from ricochet import __version__
from ricochet.core.store import InjectionStore, get_db_path

def cmd_version(args):
    """Show version and database info."""
    db_path = get_db_path()
    print(f"ricochet {__version__}")
    print(f"Database: {db_path}")
    if db_path.exists():
        print(f"Database size: {db_path.stat().st_size} bytes")
    return 0

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='ricochet',
        description='Second-order vulnerability detection tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  ricochet inject https://target.com/form
  ricochet listen --port 8080
  ricochet correlate --since 24h
        '''
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (-v for info, -vv for debug)'
    )
    parser.add_argument(
        '--db',
        type=Path,
        default=None,
        help='Database path (default: ~/.ricochet/ricochet.db)'
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        metavar='<command>'
    )

    # Placeholder subcommands for Phase 1
    # These will be expanded in later phases

    return parser

def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Initialize database on first run
    db_path = args.db or get_db_path()
    store = InjectionStore(db_path)

    return args.func(args, store) if hasattr(args, 'func') else 0

if __name__ == '__main__':
    sys.exit(main())
```

### Correlation ID Generation

```python
# Source: https://docs.python.org/3/library/secrets.html
import secrets
import time
import hashlib

def generate_correlation_id() -> str:
    """Generate a unique, URL-safe correlation ID.

    Format: 16 alphanumeric characters
    - Cryptographically random
    - Short enough to survive truncation in most contexts
    - No special characters that might be encoded/stripped
    """
    return secrets.token_hex(8)  # 16 hex chars

def generate_deterministic_id(target_url: str, param: str, secret: str) -> str:
    """Generate a deterministic ID for deduplication.

    Same inputs always produce same output.
    Useful for detecting duplicate injections.
    """
    data = f"{target_url}:{param}:{secret}:{time.time()//3600}"  # Hour-level granularity
    return hashlib.sha256(data.encode()).hexdigest()[:16]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `optparse` | `argparse` | Python 2.7/3.2 | argparse is the standard, optparse deprecated |
| Manual connection management | Context managers with `with` | Python 3.0+ | Automatic cleanup, fewer resource leaks |
| `sqlite3.connect()` default transaction | `autocommit=False` explicit | Python 3.12 | Clearer transaction semantics |
| String paths | `pathlib.Path` | Python 3.4+ | Cross-platform, object-oriented paths |
| `random` for IDs | `secrets` | Python 3.6+ | Cryptographically secure by default |

**Deprecated/outdated:**
- `optparse`: Use `argparse` instead
- String concatenation for paths: Use `pathlib`
- `random.choice()` for security tokens: Use `secrets.token_hex()`

## Open Questions

Things that couldn't be fully resolved:

1. **XDG Base Directory vs ~/.ricochet/**
   - What we know: XDG spec says use `$XDG_DATA_HOME/ricochet/` on Linux
   - What's unclear: Cross-platform behavior (Windows, macOS)
   - Recommendation: Start with `~/.ricochet/` for simplicity, consider XDG later if users request

2. **Schema Versioning/Migrations**
   - What we know: Schema will evolve across versions
   - What's unclear: How to handle upgrades without external migration libraries
   - Recommendation: Add `schema_version` table, implement simple version check on startup

3. **Concurrent Database Access**
   - What we know: SQLite supports concurrent reads, single writer
   - What's unclear: Callback server + CLI both writing simultaneously
   - Recommendation: Use WAL mode (`PRAGMA journal_mode=WAL`) for better concurrency

## Sources

### Primary (HIGH confidence)

- [Python argparse documentation](https://docs.python.org/3/library/argparse.html) - Subcommands, version action, help formatting
- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html) - Connection handling, row factory, transactions
- [Python __main__ documentation](https://docs.python.org/3/library/__main__.html) - Entry point patterns
- [SQLite Foreign Key Support](https://sqlite.org/foreignkeys.html) - PRAGMA foreign_keys requirement

### Secondary (MEDIUM confidence)

- [Python Packaging Guide: CLI Tools](https://packaging.python.org/en/latest/guides/creating-command-line-tools/) - Project structure, entry points
- [Hitchhiker's Guide: Project Structure](https://docs.python-guide.org/writing/structure/) - Package organization
- [Best Practices for Exit Codes](https://chrisdown.name/2013/11/03/exit-code-best-practises.html) - Unix conventions

### Tertiary (LOW confidence)

- Web search results for current Python CLI patterns (2025-2026) - Community practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib is well-documented, stable API
- Architecture: HIGH - Patterns from official Python documentation
- Pitfalls: MEDIUM - Some from official docs, some from community experience

**Research date:** 2026-01-29
**Valid until:** 2026-03-01 (stable domain, 30 days)
