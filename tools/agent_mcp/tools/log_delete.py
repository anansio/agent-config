"""Remove a work-log entry by id."""

from __future__ import annotations

from typing import Any

from ..log_store import read_entries, write_entries


def run(entry_id: str) -> str:
    """Remove one obsolete entry, so superseded steps do not clutter the log."""
    entries = read_entries()
    remaining = [entry for entry in entries if entry["id"] != entry_id]
    if len(remaining) == len(entries):
        raise ValueError(f"No log entry with id {entry_id}")
    write_entries(remaining)
    return entry_id


SPEC: dict[str, Any] = {
    "description": (
        "Remove an entry by id. Use it to drop a step that turned out to "
        "be a dead end, so abandoned back-and-forth does not accumulate."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_id": {"type": "string", "description": "Entry id to remove."}
        },
        "required": ["entry_id"],
    },
    "handler": run,
}
