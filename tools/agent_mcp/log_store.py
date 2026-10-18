"""Work-log storage: JSON Lines file access and entry identifiers.

Entries are stored one per line so that appending stays O(1) and reading
streams the file instead of loading it, which keeps large logs cheap.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = ".agent/log.jsonl"

# Resolved on import so the MCP server and the tests share one location, which
# tests override to run against a temporary file.
LOG_PATH = Path(os.environ.get("AGENT_LOG_PATH", DEFAULT_LOG_PATH))


def new_id() -> str:
    """Return a short random id used to reference an entry."""
    return secrets.token_hex(4)


def now_ts() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_entries() -> list[dict[str, Any]]:
    """Return every stored entry in file order. Missing file means no entries."""
    if not LOG_PATH.exists():
        return []
    entries = []
    with LOG_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def append_entry(entry: dict[str, Any]) -> None:
    """Append one entry as a single line."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_entries(entries: list[dict[str, Any]]) -> None:
    """Rewrite the log atomically, so a crash cannot leave a partial file."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOG_PATH.with_suffix(LOG_PATH.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(LOG_PATH)
