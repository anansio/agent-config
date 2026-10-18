#!/usr/bin/env python3
"""Minimal Model Context Protocol (MCP) server over stdio.

Stdlib-only on purpose: it starts anywhere `python3` is available, with no
third-party dependencies to install. Messages are newline-delimited JSON-RPC
2.0 objects on stdin/stdout, as defined by the MCP stdio transport.
"""

from __future__ import annotations

import json
import sys
from typing import Any

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "agent-tools"
SERVER_VERSION = "0.1.0"


def tool_hello(name: str = "World") -> str:
    """Return a friendly greeting. Used to verify the plugin is wired up."""
    return f"Hello, {name}! The agent-config MCP server is working."


TOOLS: dict[str, dict[str, Any]] = {
    "hello": {
        "description": (
            "Return a greeting. Use this to verify that the agent-config MCP "
            "server is reachable and its tools can be called."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name to greet. Defaults to 'World'.",
                }
            },
        },
        "handler": tool_hello,
    }
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
    except TypeError as exc:
        return {
            "content": [{"type": "text", "text": f"Invalid arguments: {exc}"}],
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
