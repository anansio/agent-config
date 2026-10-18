"""Validation tests for the plugin itself: manifest, skills, and MCP wiring.

These tests are static checks over the plugin's configuration files. They catch
the failures that unit tests on the server cannot: a broken manifest, a skill
with invalid frontmatter, a dangling reference, or an MCP command that points at
a file which does not exist.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_frontmatter(text: str) -> dict[str, str]:
    """Return the top-level key/value pairs of a YAML frontmatter block.

    Deliberately minimal: the plugin's frontmatter is flat, so a full YAML
    parser would add a dependency for nothing.
    """
    if not text.startswith("---\n"):
        return {}
    block = text.split("---\n", 2)[1]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if line and not line.startswith((" ", "\t")) and ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


class ManifestTests(unittest.TestCase):
    def test_plugin_manifest_is_valid(self) -> None:
        # Verifies the plugin can be identified and versioned, since a client
        # refuses to load a manifest without these fields.
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        for field in ("name", "version", "description", "license"):
            self.assertTrue(manifest.get(field), f"plugin.json lacks {field}")

    def test_mcp_server_starts_from_declaration(self) -> None:
        # Verifies the declared MCP command actually runs and answers the
        # handshake. This covers the real wiring path end to end, so the
        # documented manual check is not needed.
        config = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        server = config["mcpServers"]["agent-tools"]
        self.assertEqual(server["type"], "stdio")
        args = [
            arg.replace("${PLUGIN_ROOT}", str(ROOT)) for arg in server["args"]
        ]
        request = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        completed = subprocess.run(
            [server["command"], *args],
            input=request + "\n",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=server.get("cwd", str(ROOT)).replace("${PLUGIN_ROOT}", str(ROOT)),
        )
        response = json.loads(completed.stdout.splitlines()[0])
        self.assertEqual(response["result"]["serverInfo"]["name"], "agent-tools")


class SkillTests(unittest.TestCase):
    def _skill_files(self) -> list[Path]:
        return sorted((ROOT / "skills").glob("*/SKILL.md"))

    def test_each_skill_has_valid_frontmatter(self) -> None:
        # Verifies every skill can be discovered and described. Name must match
        # the directory and the description must be non-empty for the client to
        # know when to load it.
        skills = self._skill_files()
        self.assertTrue(skills, "no skills found")
        for path in skills:
            fields = parse_frontmatter(path.read_text(encoding="utf-8"))
            self.assertEqual(fields.get("name"), path.parent.name, f"{path}: name")
            self.assertTrue(fields.get("description"), f"{path}: description")

    def test_skill_relative_links_resolve(self) -> None:
        # Verifies links between skill files point at files that exist, so the
        # documented references do not rot.
        import re

        for path in self._skill_files():
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\((?!https?://)([^)]+)\)", text):
                resolved = (path.parent / target).resolve()
                self.assertTrue(resolved.exists(), f"{path}: broken link {target}")


if __name__ == "__main__":
    unittest.main()
