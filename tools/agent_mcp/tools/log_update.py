"""Rewrite an existing work-log entry by id."""

from __future__ import annotations

from typing import Any

from ..log_store import now_ts, read_entries, write_entries


def run(entry_id: str, text: str) -> str:
    """Replace the text of an existing entry, for a changed plan or wording."""
    entries = read_entries()
    for entry in entries:
        if entry["id"] == entry_id:
            entry["text"] = text
            entry["ts"] = now_ts()
            write_entries(entries)
            return entry_id
    raise ValueError(f"No log entry with id {entry_id}")


SPEC: dict[str, Any] = {
    "description": (
        "Rewrite an existing entry by id. Use it when a course change "
        "makes a recorded step obsolete or inaccurate, so the log stays "
        "consistent with the final approach."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_id": {"type": "string", "description": "Entry id to rewrite."},
            "text": {"type": "string", "description": "New entry text."},
        },
        "required": ["entry_id", "text"],
    },
    "handler": run,
}
