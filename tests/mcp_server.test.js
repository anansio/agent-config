/** Tests for the MCP server: tool handlers and the stdio protocol loop. */
import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import {
  DEFAULT_LOG_PATH,
  resolveLogPath,
} from "../tools/agent_mcp/log_store.js"
import * as log from "../tools/agent_mcp/tools/log.js"
import * as server from "../tools/agent_mcp/server.js"

const TOOLS_DIR = fileURLToPath(new URL("../tools/", import.meta.url))
const SERVER = join(TOOLS_DIR, "mcp_server.js")

// Each test gets its own log file and passes it explicitly, so tests never touch the working
// tree and stay isolated from each other.
async function withLog(t) {
  const dir = await mkdtemp(join(tmpdir(), "agent-config-log-"))
  t.after(() => rm(dir, { recursive: true, force: true }))
  return { dir, path: join(dir, "log.jsonl") }
}

test("append then search finds the entry", async (t) => {
  // The core promise of the log tool: a written entry can be read back.
  const { path } = await withLog(t)
  const entryId = log.append({ text: "raised the coverage of the parser", path })
  const found = JSON.parse(log.search({ query: "coverage", path }))

  assert.equal(found.length, 1)
  assert.equal(found[0].id, entryId)
  assert.match(found[0].text, /parser/)
})

test("append records a UTC timestamp", async (t) => {
  // Entries need a timestamp to stay ordered and reviewable over time.
  const { path } = await withLog(t)
  log.append({ text: "something", path })
  const entry = JSON.parse(log.search({ query: "", path }))[0]

  assert.ok(entry.ts.startsWith("20"))
  assert.ok(entry.ts.endsWith("+00:00"))
})

test("update rewrites the text", async (t) => {
  // A course change rewords an entry instead of adding a contradicting one.
  const { path } = await withLog(t)
  const entryId = log.append({ text: "first wording", path })
  log.update({ entry_id: entryId, text: "corrected wording", path })

  const entries = JSON.parse(log.search({ query: "", path }))
  assert.equal(entries.length, 1)
  assert.equal(entries[0].text, "corrected wording")
})

test("remove drops the entry", async (t) => {
  // Dropping abandoned attempts is what keeps the log from growing.
  const { path } = await withLog(t)
  const entryId = log.append({ text: "dead end", path })
  log.remove({ entry_id: entryId, path })

  assert.deepEqual(JSON.parse(log.search({ query: "", path })), [])
})

test("update on an unknown id fails loudly", async (t) => {
  // A wrong id must be visible to the caller, not silently ignored.
  const { path } = await withLog(t)
  assert.throws(() => log.update({ entry_id: "nope", text: "text", path }), /No log entry with id nope/)
})

test("search filters by substring", async (t) => {
  // Filtering is what keeps a large log usable.
  const { path } = await withLog(t)
  log.append({ text: "add parser", path })
  log.append({ text: "fix docs", path })

  assert.equal(JSON.parse(log.search({ query: "parser", path })).length, 1)
})

test("append keeps the kind", async (t) => {
  // The category has to survive, so a log can be filtered by kind later.
  const { path } = await withLog(t)
  log.append({ text: "add parser", path, kind: "feature" })

  assert.equal(JSON.parse(log.search({ query: "", path }))[0].kind, "feature")
})

test("append without a kind omits it", async (t) => {
  // The category is optional, so a plain entry stays lean.
  const { path } = await withLog(t)
  log.append({ text: "no category", path })

  assert.ok(!("kind" in JSON.parse(log.search({ query: "", path }))[0]))
})

test("search filters by kind", async (t) => {
  // The kind filter is what makes the category useful for review.
  const { path } = await withLog(t)
  log.append({ text: "add parser", path, kind: "feature" })
  log.append({ text: "fix parser", path, kind: "fix" })

  const matches = JSON.parse(log.search({ query: "", path, kind: "fix" }))
  assert.equal(matches.length, 1)
  assert.equal(matches[0].text, "fix parser")
})

test("update sets the kind", async (t) => {
  // A step that turns out to be a fix can be recategorized.
  const { path } = await withLog(t)
  const entryId = log.append({ text: "change", path })
  log.update({ entry_id: entryId, text: "change", path, kind: "decision" })

  assert.equal(JSON.parse(log.search({ query: "", path }))[0].kind, "decision")
})

test("the default path is project relative", () => {
  // The documented default keeps the log in the project, not next to the plugin.
  assert.equal(resolveLogPath(), DEFAULT_LOG_PATH)
  assert.equal(DEFAULT_LOG_PATH, ".agents/log.jsonl")
})

test("an explicit path wins over the default", async (t) => {
  // A project can choose where its log lives.
  const { dir } = await withLog(t)
  const target = join(dir, "nested", "log.jsonl")
  log.append({ text: "entry", path: target })

  assert.ok(JSON.parse(log.search({ query: "", path: target })).length === 1)
})

test("initialize reports the server identity", () => {
  // Clients need the identity before they can list tools.
  assert.equal(server.handleInitialize({}).serverInfo.name, server.SERVER_NAME)
})

test("tools/list advertises every log tool with a schema", () => {
  // Discovery is what lets the client call the tools at all.
  const tools = server.handleToolsList().tools
  assert.deepEqual(
    tools.map((tool) => tool.name).sort(),
    ["log_append", "log_delete", "log_search", "log_update"],
  )
  for (const tool of tools) assert.ok(tool.inputSchema)
})

test("an unknown tool is a structured error", () => {
  // A wrong name must not crash the transport.
  const result = server.handleToolsCall({ name: "does_not_exist" })
  assert.equal(result.isError, true)
  assert.match(result.content[0].text, /Unknown tool/)
})

test("a missing required argument is a structured error", () => {
  // Arguments arrive as untrusted data; a missing field must be reported, not thrown at the loop.
  const result = server.handleToolsCall({ name: "log_append", arguments: {} })
  assert.equal(result.isError, true)
  assert.match(result.content[0].text, /Invalid call/)
})

test("dispatch rejects an unsupported method", () => {
  // The loop turns this into a JSON-RPC error response.
  assert.throws(() => server.dispatch("nope", {}), /Method not found/)
})

test("stdio end to end", async (t) => {
  // The real process has to answer over stdin/stdout the documented way, including a tool call
  // that writes an entry: this covers the full path a client uses.
  const { path } = await withLog(t)
  const requests = [
    { jsonrpc: "2.0", method: "notifications/initialized" },
    { jsonrpc: "2.0", id: 1, method: "initialize", params: {} },
    { jsonrpc: "2.0", id: 2, method: "tools/list" },
    {
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: { name: "log_append", arguments: { text: "end to end entry", path } },
    },
    {
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: { name: "log_search", arguments: { query: "", path } },
    },
  ]
    .map((message) => JSON.stringify(message))
    .join("\n")

  const stdout = execFileSync(process.execPath, [SERVER], {
    input: requests + "\n",
    encoding: "utf8",
    timeout: 10000,
  })
  const lines = stdout.trim().split("\n").map((line) => JSON.parse(line))

  // The notification is unanswered, so four requests produce four responses.
  assert.equal(lines.length, 4)
  assert.equal(lines[0].result.serverInfo.name, server.SERVER_NAME)
  assert.equal(lines[1].result.tools.length, 4)

  const entryId = lines[2].result.content[0].text
  const entries = JSON.parse(lines[3].result.content[0].text)
  assert.equal(entries[0].id, entryId)
  assert.equal(entries[0].text, "end to end entry")
})
