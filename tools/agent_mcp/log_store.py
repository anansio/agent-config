"""Work-log storage: JSON Lines file access and entry identifiers.

Entries are stored one per line so that appending stays O(1) and reading
streams the file instead of loading it, which keeps large logs cheap.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Default location, relative to the project the agent works in. Tools accept an
# explicit path to place the log anywhere else.
DEFAULT_LOG_PATH = ".agents/log.jsonl"


def resolve_log_path(path: str | None = None) -> Path:
    """Return the log file to use: the given path, or the project default."""
    return Path(path).expanduser() if path else Path(DEFAULT_LOG_PATH)


def new_id() -> str:
    """Return a short random id used to reference an entry."""
    return secrets.token_hex(4)


def now_ts() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_entries(log_path: Path) -> list[dict[str, Any]]:
    """Return every stored entry in file order. Missing file means no entries."""
    if not log_path.exists():
        return []
    entries = []
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def append_entry(log_path: Path, entry: dict[str, Any]) -> None:
    """Append one entry as a single line."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_entries(log_path: Path, entries: list[dict[str, Any]]) -> None:
    """Rewrite the log atomically, so a crash cannot leave a partial file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = log_path.with_suffix(log_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(log_path)
