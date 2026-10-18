#!/usr/bin/env python3
"""Stdio entry point for the agent-tools MCP server.

Kept as a thin launcher so the MCP declaration in `mcp.json` can point at a
stable file while the implementation lives in the `agent_mcp` package.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (python3 tools/mcp_server.py) by making the
# sibling package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_mcp import main  # noqa: E402

if __name__ == "__main__":
    main()
