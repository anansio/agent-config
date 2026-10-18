"""Registration and JSON-RPC entry point for the agent-tools MCP server."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .tools import log

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "agent-tools"
SERVER_VERSION = "0.1.0"

# Each tool group contributes its specs; the server only wires them into the
# protocol, so adding a group means importing it here.
TOOLS: dict[str, dict[str, Any]] = dict(log.SPECS)


def handle_initialize(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def handle_tools_list() -> dict[str, Any]:
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


def handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
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


def dispatch(method: str, params: dict[str, Any]) -> Any:
    handlers: dict[str, Callable[[], Any]] = {
        "initialize": lambda: handle_initialize(params),
        "tools/list": handle_tools_list,
        "tools/call": lambda: handle_tools_call(params),
        "ping": dict,
    }
    if method not in handlers:
        raise ValueError(f"Method not found: {method}")
    return handlers[method]()


def _send(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> None:
    """Read newline-delimited JSON-RPC messages from stdin and answer on stdout."""
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
            result = dispatch(method, message.get("params") or {})
            _send({"jsonrpc": "2.0", "id": msg_id, "result": result})
        except Exception as exc:  # noqa: BLE001 - report any failure to the client
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(exc)},
                }
            )
