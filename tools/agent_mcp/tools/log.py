"""The work-log tool group: append, update, delete, and search entries."""

from __future__ import annotations

import json
from typing import Any

from ..log_store import append_entry, new_id, now_ts, read_entries, write_entries


def append(text: str) -> str:
    """Append one work-log entry and return its id."""
    entry = {"id": new_id(), "ts": now_ts(), "text": text}
    append_entry(entry)
    return entry["id"]


def update(entry_id: str, text: str) -> str:
    """Replace the text of an existing entry, for a changed plan or wording."""
    entries = read_entries()
    for entry in entries:
        if entry["id"] == entry_id:
            entry["text"] = text
            entry["ts"] = now_ts()
            write_entries(entries)
            return entry_id
    raise ValueError(f"No log entry with id {entry_id}")


def delete(entry_id: str) -> str:
    """Remove one obsolete entry, so superseded steps do not clutter the log."""
    entries = read_entries()
    remaining = [entry for entry in entries if entry["id"] != entry_id]
    if len(remaining) == len(entries):
        raise ValueError(f"No log entry with id {entry_id}")
    write_entries(remaining)
    return entry_id


def search(query: str = "") -> str:
    """Return matching entries as compact JSON. An empty query returns all."""
    needle = query.lower()
    matches = [
        {"id": entry["id"], "ts": entry["ts"], "text": entry["text"]}
        for entry in read_entries()
        if needle in entry["text"].lower()
    ]
    return json.dumps(matches, ensure_ascii=False)


# Tool specs registered by the server: MCP name -> description, schema, handler.
SPECS: dict[str, dict[str, Any]] = {
    "log_append": {
        "description": (
            "Append a short work-log entry: what was done and why. Record "
            "meaningful intermediate steps during the work, not only the end "
            "result. Keep one entry short and factual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Short entry: what was done and why.",
                }
            },
            "required": ["text"],
        },
        "handler": append,
    },
    "log_update": {
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
        "handler": update,
    },
    "log_delete": {
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
        "handler": delete,
    },
    "log_search": {
        "description": (
            "Search entries by substring and return them with their ids, to "
            "review the log or find an entry to update or delete."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Substring to match. Empty returns all entries.",
                }
            },
        },
        "handler": search,
    },
}
