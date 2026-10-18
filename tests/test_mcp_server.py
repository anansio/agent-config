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
from agent_mcp.tools import log  # noqa: E402


class LogToolTests(unittest.TestCase):
    def setUp(self) -> None:
        # Each test gets its own log file and passes it explicitly, so tests
        # never touch the working tree and stay isolated from each other.
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "log.jsonl")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_append_then_search(self) -> None:
        # Verifies a written entry can be read back. This is the core promise
        # of the log tool, so it must work end to end.
        entry_id = log.append("raised the coverage of the parser", self.path)
        found = json.loads(log.search("coverage", self.path))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], entry_id)
        self.assertIn("parser", found[0]["text"])

    def test_append_records_timestamp(self) -> None:
        # Verifies every entry carries a UTC timestamp, since the log needs to
        # stay ordered and reviewable over time.
        log.append("something", self.path)
        entry = json.loads(log.search("", self.path))[0]
        self.assertIn("ts", entry)
        self.assertTrue(entry["ts"].startswith("20"))

    def test_update_rewrites_text(self) -> None:
        # Verifies an entry can be reworded after a course change, keeping the
        # log consistent instead of adding a contradicting entry.
        entry_id = log.append("first wording", self.path)
        log.update(entry_id, "corrected wording", self.path)
        entries = json.loads(log.search("", self.path))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["text"], "corrected wording")

    def test_delete_removes_entry(self) -> None:
        # Verifies an obsolete entry can be dropped, which is what keeps the
        # log from growing with abandoned attempts.
        entry_id = log.append("dead end", self.path)
        log.delete(entry_id, self.path)
        self.assertEqual(json.loads(log.search("", self.path)), [])

    def test_update_unknown_id_raises(self) -> None:
        # Verifies editing a missing entry fails loudly rather than silently
        # doing nothing, so a wrong id is visible to the caller.
        with self.assertRaises(ValueError):
            log.update("nope", "text", self.path)

    def test_search_filters_by_substring(self) -> None:
        # Verifies search narrows results, since filtering is what keeps a
        # large log usable.
        log.append("add parser", self.path)
        log.append("fix docs", self.path)
        self.assertEqual(len(json.loads(log.search("parser", self.path))), 1)

    def test_default_path_is_project_relative(self) -> None:
        # Verifies the documented default is used when no path is given, so
        # the log lands in the project rather than next to the plugin.
        self.assertEqual(str(log_store.resolve_log_path()), log_store.DEFAULT_LOG_PATH)
        self.assertEqual(log_store.DEFAULT_LOG_PATH, ".agents/log.jsonl")

    def test_explicit_path_is_used(self) -> None:
        # Verifies a given path wins over the default, which is how a project
        # chooses where its log lives.
        target = Path(self._tmp.name) / "nested" / "log.jsonl"
        log.append("entry", str(target))
        self.assertTrue(target.is_file())


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
        # Verifies the real process answers over stdin/stdout the documented
        # way and that a tool call writes an entry, covering the full path a
        # client uses without any manual check.
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.jsonl"
            requests = "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "log_append",
                                "arguments": {"text": "end to end entry", "path": str(log_path)},
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 4,
                            "method": "tools/call",
                            "params": {
                                "name": "log_search",
                                "arguments": {"query": "", "path": str(log_path)},
                            },
                        }
                    ),
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
            # The append call returns an id, and the search call returns the entry.
            entry_id = lines[2]["result"]["content"][0]["text"]
            entries = json.loads(lines[3]["result"]["content"][0]["text"])
            self.assertEqual(entries[0]["id"], entry_id)
            self.assertEqual(entries[0]["text"], "end to end entry")
            self.assertTrue(log_path.is_file())


if __name__ == "__main__":
    unittest.main()
