"""The work-log tool group: append, update, delete, and search entries."""

from __future__ import annotations

import json
from typing import Any

from ..log_store import (
    resolve_log_path,
    append_entry,
    new_id,
    now_ts,
    read_entries,
    write_entries,
)

# Every tool accepts an optional path so a project can keep its log outside the
# default location. The description is shared so the wording stays in one place.
PATH_DESCRIPTION = (
    "Path to the log file. Omit it to use '.agents/log.jsonl' in the project "
    "directory."
)

KIND_DESCRIPTION = (
    "Optional category, for filtering: 'feature', 'fix', or 'decision'."
)


def append(text: str, path: str | None = None, kind: str | None = None) -> str:
    """Append one work-log entry and return its id."""
    log_path = resolve_log_path(path)
    entry = {"id": new_id(), "ts": now_ts(), "text": text}
    if kind:
        entry["kind"] = kind
    append_entry(log_path, entry)
    return entry["id"]


def update(
    entry_id: str,
    text: str,
    path: str | None = None,
    kind: str | None = None,
) -> str:
    """Replace the text of an existing entry, for a changed plan or wording."""
    log_path = resolve_log_path(path)
    entries = read_entries(log_path)
    for entry in entries:
        if entry["id"] == entry_id:
            entry["text"] = text
            entry["ts"] = now_ts()
            if kind:
                entry["kind"] = kind
            write_entries(log_path, entries)
            return entry_id
    raise ValueError(f"No log entry with id {entry_id}")


def delete(entry_id: str, path: str | None = None) -> str:
    """Remove one obsolete entry, so superseded steps do not clutter the log."""
    log_path = resolve_log_path(path)
    entries = read_entries(log_path)
    remaining = [entry for entry in entries if entry["id"] != entry_id]
    if len(remaining) == len(entries):
        raise ValueError(f"No log entry with id {entry_id}")
    write_entries(log_path, remaining)
    return entry_id


def search(
    query: str = "",
    path: str | None = None,
    kind: str | None = None,
) -> str:
    """Return matching entries as compact JSON. An empty query returns all.

    A kind narrows the result to entries of that category.
    """
    log_path = resolve_log_path(path)
    needle = query.lower()
    matches = []
    for entry in read_entries(log_path):
        if needle and needle not in entry["text"].lower():
            continue
        if kind and entry.get("kind") != kind:
            continue
        result = {"id": entry["id"], "ts": entry["ts"], "text": entry["text"]}
        if entry.get("kind"):
            result["kind"] = entry["kind"]
        matches.append(result)
    return json.dumps(matches, ensure_ascii=False)


# Tool specs registered by the server: MCP name -> description, schema, handler.
SPECS: dict[str, dict[str, Any]] = {
    "log_append": {
        "description": (
            "Append a short work-log entry: a feature, a fix, or a decision. "
            "Record meaningful milestones, not every step. Writes to "
            "'.agents/log.jsonl' in the project directory unless a different "
            "path is given."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Short entry: what was done and why.",
                },
                "kind": {"type": "string", "description": KIND_DESCRIPTION},
                "path": {"type": "string", "description": PATH_DESCRIPTION},
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
                "kind": {"type": "string", "description": KIND_DESCRIPTION},
                "path": {"type": "string", "description": PATH_DESCRIPTION},
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
                "entry_id": {"type": "string", "description": "Entry id to remove."},
                "path": {"type": "string", "description": PATH_DESCRIPTION},
            },
            "required": ["entry_id"],
        },
        "handler": delete,
    },
    "log_search": {
        "description": (
            "Search entries by substring and return them with their ids, to "
            "review the log or find an entry to update or delete. A kind "
            "narrows the result to one category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Substring to match. Empty returns all entries.",
                },
                "kind": {"type": "string", "description": KIND_DESCRIPTION},
                "path": {"type": "string", "description": PATH_DESCRIPTION},
            },
        },
        "handler": search,
    },
}
