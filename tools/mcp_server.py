#!/usr/bin/env python3
"""Minimal Model Context Protocol (MCP) server over stdio.

Stdlib-only on purpose: it starts anywhere `python3` is available, with no
third-party dependencies to install. Messages are newline-delimited JSON-RPC
2.0 objects on stdin/stdout, as defined by the MCP stdio transport.

The server exposes a small work-log tool set. Entries are stored as JSON Lines
(one entry per line) so that appending stays O(1) and searching streams the
file instead of loading it, which keeps large logs cheap to work with.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "agent-tools"
SERVER_VERSION = "0.2.0"

DEFAULT_LOG_PATH = ".agent/log.jsonl"
LOG_PATH = Path(os.environ.get("AGENT_LOG_PATH", DEFAULT_LOG_PATH))


def _read_entries() -> list[dict[str, Any]]:
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


def _write_entries(entries: list[dict[str, Any]]) -> None:
    """Rewrite the log atomically, so a crash cannot leave a partial file."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOG_PATH.with_suffix(LOG_PATH.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(LOG_PATH)


def _new_id() -> str:
    return secrets.token_hex(4)


def log_append(text: str) -> str:
    """Append one work-log entry and return its id."""
    entry = {
        "id": _new_id(),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "text": text,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry["id"]


def log_update(entry_id: str, text: str) -> str:
    """Replace the text of an existing entry, for a changed plan or wording."""
    entries = _read_entries()
    for entry in entries:
        if entry["id"] == entry_id:
            entry["text"] = text
            entry["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            _write_entries(entries)
            return entry_id
    raise ValueError(f"No log entry with id {entry_id}")


def log_delete(entry_id: str) -> str:
    """Remove one obsolete entry, so superseded steps do not clutter the log."""
    entries = _read_entries()
    remaining = [entry for entry in entries if entry["id"] != entry_id]
    if len(remaining) == len(entries):
        raise ValueError(f"No log entry with id {entry_id}")
    _write_entries(remaining)
    return entry_id


def log_search(query: str = "") -> str:
    """Return matching entries as compact JSON. An empty query returns all."""
    needle = query.lower()
    matches = [
        {"id": entry["id"], "ts": entry["ts"], "text": entry["text"]}
        for entry in _read_entries()
        if needle in entry["text"].lower()
    ]
    return json.dumps(matches, ensure_ascii=False)


TOOLS: dict[str, dict[str, Any]] = {
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
        "handler": log_append,
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
        "handler": log_update,
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
        "handler": log_delete,
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
        "handler": log_search,
    },
}


def _handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def _handle_tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["input_schema"],
            }
            for name, spec in TOOLS.items()
        ]
    }


def _handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    spec = TOOLS.get(name)

    if spec is None:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }

    try:
        result = spec["handler"](**arguments)
    except (TypeError, ValueError) as exc:
        return {
            "content": [{"type": "text", "text": f"Invalid call: {exc}"}],
            "isError": True,
        }

    return {"content": [{"type": "text", "text": str(result)}]}


def _dispatch(method: str, params: dict[str, Any]) -> Any:
    if method == "initialize":
        return _handle_initialize(params)
    if method == "tools/list":
        return _handle_tools_list()
    if method == "tools/call":
        return _handle_tools_call(params)
    if method == "ping":
        return {}
    raise ValueError(f"Method not found: {method}")


def _send(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = message.get("method")
        msg_id = message.get("id")

        # Notifications carry no id and expect no response.
        if msg_id is None:
            continue

        try:
            result = _dispatch(method, message.get("params") or {})
            _send({"jsonrpc": "2.0", "id": msg_id, "result": result})
        except Exception as exc:  # noqa: BLE001 - report any failure to the client
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(exc)},
                }
            )


if __name__ == "__main__":
    main()
