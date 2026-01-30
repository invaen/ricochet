"""
Payload file loading for custom wordlists and payload files.

Supports loading payloads from SecLists, Wfuzz, and other standard wordlist
formats. Files should contain one payload per line, with # for comments
and blank lines being skipped.

File format:
    # This is a comment
    payload1
    payload2

    # Another comment
    payload3{{CALLBACK}}

The {{CALLBACK}} placeholder in payloads will be substituted with the
actual callback URL during injection.
"""

from pathlib import Path
from typing import Iterator


def load_payloads(filepath: Path) -> list[str]:
    """Load payloads from a file into a list.

    Reads the entire file into memory. For very large files (100k+ lines),
    consider using load_payloads_streaming() instead.

    File format:
        - One payload per line
        - Lines starting with # are treated as comments and skipped
        - Blank lines are skipped
        - Only trailing newlines are stripped (leading whitespace preserved)

    Compatible with:
        - SecLists wordlists
        - Wfuzz wordlists
        - Any text file with one payload per line

    Args:
        filepath: Path to the payload file

    Returns:
        List of payload strings

    Raises:
        FileNotFoundError: If the file doesn't exist
        UnicodeDecodeError: If the file isn't valid UTF-8

    Example:
        >>> payloads = load_payloads(Path("payloads.txt"))
        >>> for payload in payloads:
        ...     inject(payload)
    """
    payloads = []

    with filepath.open('r', encoding='utf-8') as f:
        for line in f:
            # Strip only trailing newlines, preserve other whitespace
            line = line.rstrip('\n\r')

            # Skip comments
            if line.startswith('#'):
                continue

            # Skip empty lines
            if not line:
                continue

            payloads.append(line)

    return payloads


def load_payloads_streaming(filepath: Path) -> Iterator[str]:
    """Load payloads from a file as a generator.

    Memory-efficient version that yields payloads one at a time instead
    of loading the entire file into memory. Ideal for large wordlists.

    File format:
        - One payload per line
        - Lines starting with # are treated as comments and skipped
        - Blank lines are skipped
        - Only trailing newlines are stripped (leading whitespace preserved)

    Compatible with:
        - SecLists wordlists
        - Wfuzz wordlists
        - Any text file with one payload per line

    Args:
        filepath: Path to the payload file

    Yields:
        Payload strings one at a time

    Raises:
        FileNotFoundError: If the file doesn't exist
        UnicodeDecodeError: If the file isn't valid UTF-8

    Example:
        >>> for payload in load_payloads_streaming(Path("huge-wordlist.txt")):
        ...     inject(payload)
    """
    with filepath.open('r', encoding='utf-8') as f:
        for line in f:
            # Strip only trailing newlines, preserve other whitespace
            line = line.rstrip('\n\r')

            # Skip comments
            if line.startswith('#'):
                continue

            # Skip empty lines
            if not line:
                continue

            yield line
