/** Registration and JSON-RPC entry point for the agent-tools MCP server. */
import { createInterface } from "node:readline"
import { SPECS } from "./tools/log.js"

export const PROTOCOL_VERSION = "2024-11-05"
export const SERVER_NAME = "agent-tools"
export const SERVER_VERSION = "0.3.0"

// Each tool group contributes its specs; the server only wires them into the
// protocol, so adding a group means importing it here.
export const TOOLS = { ...SPECS }

export function handleInitialize(params = {}) {
  return {
    protocolVersion: params.protocolVersion || PROTOCOL_VERSION,
    capabilities: { tools: {} },
    serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
  }
}

export function handleToolsList() {
  return {
    tools: Object.entries(TOOLS).map(([name, spec]) => ({
      name,
      description: spec.description,
      inputSchema: spec.inputSchema,
    })),
  }
}

export function handleToolsCall(params = {}) {
  const name = params.name
  const args = params.arguments ?? {}
  const spec = TOOLS[name]

  if (!spec) {
    return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true }
  }

  try {
    return { content: [{ type: "text", text: String(spec.handler(args)) }] }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return { content: [{ type: "text", text: `Invalid call: ${message}` }], isError: true }
  }
}

export function dispatch(method, params = {}) {
  const handlers = {
    initialize: () => handleInitialize(params),
    "tools/list": () => handleToolsList(),
    "tools/call": () => handleToolsCall(params),
    ping: () => ({}),
  }
  const handler = handlers[method]
  if (!handler) throw new Error(`Method not found: ${method}`)
  return handler()
}

function send(output, payload) {
  output.write(JSON.stringify(payload) + "\n")
}

/** Read newline-delimited JSON-RPC messages from input and answer on output. */
export function main(input = process.stdin, output = process.stdout) {
  const lines = createInterface({ input, crlfDelay: Infinity })

  lines.on("line", (line) => {
    const trimmed = line.trim()
    if (!trimmed) return

    let message
    try {
      message = JSON.parse(trimmed)
    } catch {
      return
    }

    const id = message.id
    // Notifications carry no id and expect no response.
    if (id === undefined || id === null) return

    try {
      send(output, { jsonrpc: "2.0", id, result: dispatch(message.method, message.params || {}) })
    } catch (error) {
      const text = error instanceof Error ? error.message : String(error)
      send(output, { jsonrpc: "2.0", id, error: { code: -32603, message: text } })
    }
  })
}
