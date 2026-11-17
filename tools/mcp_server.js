#!/usr/bin/env node
/**
 * Stdio entry point for the agent-tools MCP server.
 *
 * Kept as a thin launcher so the MCP declaration in `mcp.json` can point at a
 * stable file while the implementation lives in the `agent_mcp` directory.
 */
import { main } from "./agent_mcp/server.js"

main()
