"""Tests for the MCP server: tool handlers and the stdio protocol loop."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import mcp_server  # noqa: E402


class LogToolTests(unittest.TestCase):
    def setUp(self) -> None:
        # Redirect the module's log path into a temp file so tests never touch
        # the working tree and stay isolated from each other.
        self._tmp = tempfile.TemporaryDirectory()
        self._original = mcp_server.LOG_PATH
        mcp_server.LOG_PATH = Path(self._tmp.name) / "log.jsonl"

    def tearDown(self) -> None:
        mcp_server.LOG_PATH = self._original
        self._tmp.cleanup()

    def test_append_then_search(self) -> None:
        # Verifies a written entry can be read back. This is the core promise
        # of the log tool, so it must work end to end.
        entry_id = mcp_server.log_append("raised the coverage of the parser")
        found = json.loads(mcp_server.log_search("coverage"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], entry_id)
        self.assertIn("parser", found[0]["text"])

    def test_update_rewrites_text(self) -> None:
        # Verifies an entry can be reworded after a course change, keeping the
        # log consistent instead of adding a contradicting entry.
        entry_id = mcp_server.log_append("first wording")
        mcp_server.log_update(entry_id, "corrected wording")
        entries = json.loads(mcp_server.log_search(""))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "corrected wording")

    def test_delete_removes_entry(self) -> None:
        # Verifies an obsolete entry can be dropped, which is what keeps the
        # log from growing with abandoned attempts.
        entry_id = mcp_server.log_append("dead end")
        mcp_server.log_delete(entry_id)
        self.assertEqual(json.loads(mcp_server.log_search("")), [])

    def test_update_unknown_id_raises(self) -> None:
        # Verifies editing a missing entry fails loudly rather than silently
        # doing nothing, so a wrong id is visible to the caller.
        with self.assertRaises(ValueError):
            mcp_server.log_update("nope", "text")

    def test_search_filters_by_substring(self) -> None:
        # Verifies search narrows results, since filtering is what keeps a
        # large log usable.
        mcp_server.log_append("add parser")
        mcp_server.log_append("fix docs")
        self.assertEqual(len(json.loads(mcp_server.log_search("parser"))), 1)


class ProtocolTests(unittest.TestCase):
    def test_initialize_reports_server(self) -> None:
        # Verifies the handshake returns the server identity, which clients
        # need before they can list tools.
        result = mcp_server._handle_initialize({})
        self.assertEqual(result["serverInfo"]["name"], mcp_server.SERVER_NAME)

    def test_tools_list_exposes_log_tools(self) -> None:
        # Verifies every log tool is advertised with a schema, so the client
        # can discover and call them.
        names = {tool["name"] for tool in mcp_server._handle_tools_list()["tools"]}
        self.assertEqual(
            names, {"log_append", "log_update", "log_delete", "log_search"}
        )
        self.assertIn("inputSchema", mcp_server._handle_tools_list()["tools"][0])

    def test_unknown_tool_is_error(self) -> None:
        # Verifies an unknown tool name yields a structured error instead of a
        # crash, keeping the transport responsive.
        result = mcp_server._handle_tools_call({"name": "does_not_exist"})
        self.assertTrue(result["isError"])

    def test_dispatch_unknown_method_raises(self) -> None:
        # Verifies an unsupported JSON-RPC method is rejected, which the main
        # loop turns into an error response.
        with self.assertRaises(ValueError):
            mcp_server._dispatch("nope", {})

    def test_stdio_end_to_end(self) -> None:
        # Verifies the real process answers over stdin/stdout in the documented
        # way, covering the part unit tests cannot reach.
        root = Path(__file__).resolve().parent.parent
        requests = "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            ]
        )
        completed = subprocess.run(
            [sys.executable, str(root / "tools" / "mcp_server.py")],
            input=requests + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], mcp_server.SERVER_NAME)
        self.assertEqual(len(lines[1]["result"]["tools"]), 4)


if __name__ == "__main__":
    unittest.main()
