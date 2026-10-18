"""Tests for the MCP server: tool handlers and the stdio protocol loop."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from agent_mcp import log_store, server  # noqa: E402
from agent_mcp.tools import log_append, log_delete, log_search, log_update  # noqa: E402


class LogToolTests(unittest.TestCase):
    def setUp(self) -> None:
        # Point the store at a temp file so tests never touch the working tree
        # and stay isolated from each other.
        self._tmp = tempfile.TemporaryDirectory()
        self._original = log_store.LOG_PATH
        log_store.LOG_PATH = Path(self._tmp.name) / "log.jsonl"

    def tearDown(self) -> None:
        log_store.LOG_PATH = self._original
        self._tmp.cleanup()

    def test_append_then_search(self) -> None:
        # Verifies a written entry can be read back. This is the core promise
        # of the log tool, so it must work end to end.
        entry_id = log_append.run("raised the coverage of the parser")
        found = json.loads(log_search.run("coverage"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], entry_id)
        self.assertIn("parser", found[0]["text"])

    def test_append_records_timestamp(self) -> None:
        # Verifies every entry carries a UTC timestamp, since the log needs to
        # stay ordered and reviewable over time.
        log_append.run("something")
        entry = json.loads(log_search.run(""))[0]
        self.assertIn("ts", entry)
        self.assertTrue(entry["ts"].startswith("20"))

    def test_update_rewrites_text(self) -> None:
        # Verifies an entry can be reworded after a course change, keeping the
        # log consistent instead of adding a contradicting entry.
        entry_id = log_append.run("first wording")
        log_update.run(entry_id, "corrected wording")
        entries = json.loads(log_search.run(""))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "corrected wording")

    def test_delete_removes_entry(self) -> None:
        # Verifies an obsolete entry can be dropped, which is what keeps the
        # log from growing with abandoned attempts.
        entry_id = log_append.run("dead end")
        log_delete.run(entry_id)
        self.assertEqual(json.loads(log_search.run("")), [])

    def test_update_unknown_id_raises(self) -> None:
        # Verifies editing a missing entry fails loudly rather than silently
        # doing nothing, so a wrong id is visible to the caller.
        with self.assertRaises(ValueError):
            log_update.run("nope", "text")

    def test_search_filters_by_substring(self) -> None:
        # Verifies search narrows results, since filtering is what keeps a
        # large log usable.
        log_append.run("add parser")
        log_append.run("fix docs")
        self.assertEqual(len(json.loads(log_search.run("parser"))), 1)


class ProtocolTests(unittest.TestCase):
    def test_initialize_reports_server(self) -> None:
        # Verifies the handshake returns the server identity, which clients
        # need before they can list tools.
        result = server.handle_initialize({})
        self.assertEqual(result["serverInfo"]["name"], server.SERVER_NAME)

    def test_tools_list_exposes_log_tools(self) -> None:
        # Verifies every log tool is advertised with a schema, so the client
        # can discover and call them.
        tools = server.handle_tools_list()["tools"]
        names = {tool["name"] for tool in tools}
        self.assertEqual(
            names, {"log_append", "log_update", "log_delete", "log_search"}
        )
        self.assertIn("inputSchema", tools[0])

    def test_unknown_tool_is_error(self) -> None:
        # Verifies an unknown tool name yields a structured error instead of a
        # crash, keeping the transport responsive.
        result = server.handle_tools_call({"name": "does_not_exist"})
        self.assertTrue(result["isError"])

    def test_dispatch_unknown_method_raises(self) -> None:
        # Verifies an unsupported JSON-RPC method is rejected, which the main
        # loop turns into an error response.
        with self.assertRaises(ValueError):
            server.dispatch("nope", {})

    def test_stdio_end_to_end(self) -> None:
        # Verifies the real process answers over stdin/stdout in the documented
        # way, covering the part unit tests cannot reach.
        requests = "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
            ]
        )
        completed = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "mcp_server.py")],
            input=requests + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(lines[0]["result"]["serverInfo"]["name"], server.SERVER_NAME)
        self.assertEqual(len(lines[1]["result"]["tools"]), 4)


if __name__ == "__main__":
    unittest.main()
