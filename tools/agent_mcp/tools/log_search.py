"""Search work-log entries by substring."""

from __future__ import annotations

import json
from typing import Any

from ..log_store import read_entries


def run(query: str = "") -> str:
    """Return matching entries as compact JSON. An empty query returns all."""
    needle = query.lower()
    matches = [
        {"id": entry["id"], "ts": entry["ts"], "text": entry["text"]}
        for entry in read_entries()
        if needle in entry["text"].lower()
    ]
    return json.dumps(matches, ensure_ascii=False)


SPEC: dict[str, Any] = {
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
    "handler": run,
}
