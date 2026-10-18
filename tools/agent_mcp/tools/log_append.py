"""Append a new entry to the work log."""

from __future__ import annotations

from typing import Any

from ..log_store import append_entry, new_id, now_ts


def run(text: str) -> str:
    """Append one work-log entry and return its id."""
    entry = {"id": new_id(), "ts": now_ts(), "text": text}
    append_entry(entry)
    return entry["id"]


SPEC: dict[str, Any] = {
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
    "handler": run,
}
