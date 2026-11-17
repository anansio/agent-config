/**
 * Validation tests for the plugin itself: manifest, skills, and MCP wiring.
 *
 * These are static checks over the plugin's configuration files. They catch the failures that
 * unit tests on the server cannot: a broken manifest, a skill with invalid frontmatter, a
 * dangling reference, or an MCP command that points at a file which does not exist.
 */
import assert from "node:assert/strict"
import { execFileSync } from "node:child_process"
import { existsSync, readdirSync, readFileSync } from "node:fs"
import { basename, dirname, join, resolve } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)))

/**
 * Return the top-level key/value pairs of a YAML frontmatter block. Deliberately minimal: the
 * plugin's frontmatter is flat, so a full YAML parser would add a dependency for nothing.
 */
function parseFrontmatter(text) {
  if (!text.startsWith("---\n")) return {}
  const block = text.split("---\n")[1] ?? ""
  const fields = {}
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(" ") || line.startsWith("\t") || !line.includes(":")) continue
    const [key, ...rest] = line.split(":")
    fields[key.trim()] = rest.join(":").trim()
  }
  return fields
}

function skillFiles(dir = join(ROOT, "skills")) {
  return readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => join(dir, entry.name, "SKILL.md"))
    .sort()
}

function walk(dir, results = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === ".git" || entry.name === "node_modules") continue
    const path = join(dir, entry.name)
    if (entry.isDirectory()) walk(path, results)
    else results.push(path)
  }
  return results
}

test("the plugin manifest identifies and versions the plugin", () => {
  // A client refuses to load a manifest without these fields.
  const manifest = JSON.parse(readFileSync(join(ROOT, "plugin.json"), "utf8"))
  for (const field of ["name", "version", "description", "license"]) {
    assert.ok(manifest[field], `plugin.json lacks ${field}`)
  }
})

test("the declared MCP server starts over stdio", () => {
  // The declaration has to point at a runnable file with the right interpreter; anything less is
  // a broken install that only shows up in a user's client.
  const config = JSON.parse(readFileSync(join(ROOT, "mcp.json"), "utf8"))
  const declared = config.mcpServers["agent-tools"]
  assert.equal(declared.type, "stdio")
  assert.equal(declared.command, "node")
  assert.deepEqual(declared.args, ["${PLUGIN_ROOT}/tools/mcp_server.js"])

  const args = declared.args.map((arg) => arg.replaceAll("${PLUGIN_ROOT}", ROOT))
  const request = JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: {} })
  const stdout = execFileSync(declared.command, args, {
    input: request + "\n",
    encoding: "utf8",
    timeout: 10000,
    cwd: ROOT,
  })
  const response = JSON.parse(stdout.split("\n")[0])
  assert.equal(response.result.serverInfo.name, "agent-tools")
})

test("every skill has valid frontmatter", () => {
  // Name must match the directory and the description must be non-empty for the client to know
  // when to load the skill.
  const skills = skillFiles()
  assert.ok(skills.length > 0, "no skills found")
  for (const path of skills) {
    const fields = parseFrontmatter(readFileSync(path, "utf8"))
    assert.equal(fields.name, basename(dirname(path)), `${path}: name`)
    assert.ok(fields.description, `${path}: description`)
  }
})

test("skill frontmatter uses only allowed fields", () => {
  // Agent Skills defines a closed set of fields. A conforming client MUST skip a skill carrying
  // anything else, so a stray client-specific field silently drops the skill.
  const allowed = new Set(["name", "description", "license", "compatibility", "metadata", "allowed-tools"])
  for (const path of skillFiles()) {
    const fields = parseFrontmatter(readFileSync(path, "utf8"))
    const extra = Object.keys(fields).filter((field) => !allowed.has(field))
    assert.deepEqual(extra, [], `${path}: unsupported frontmatter field(s) ${extra}`)
  }
})

test("relative skill links resolve", () => {
  // Links between skill files must point at files that exist, so the references do not rot.
  for (const path of skillFiles()) {
    const text = readFileSync(path, "utf8")
    for (const [, target] of text.matchAll(/\]\((?!https?:\/\/)([^)]+)\)/g)) {
      const resolved = resolve(dirname(path), target)
      assert.ok(existsSync(resolved), `${path}: broken link ${target}`)
    }
  }
})

test("the project carries no Python files", () => {
  // The runtime and the test suite are one language. A stray .py file would reintroduce the
  // second code path this repository deliberately avoids.
  const python = walk(ROOT).filter((path) => path.endsWith(".py"))
  assert.deepEqual(python, [], `unexpected Python files: ${python.join(", ")}`)
})
