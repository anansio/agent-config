import assert from "node:assert/strict"
import { mkdtemp, rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import { isAbsolute, join, resolve } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import {
  loadMcpServers,
  loadRules,
  loadSkills,
  splitFrontmatter,
  RULES_SKILL,
  type McpServerConfig,
} from "../opencode/lib.ts"

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)))
const SKILLS = join(ROOT, "skills")

function local(config: McpServerConfig) {
  if (config.type !== "local") throw new Error(`expected a local server, got ${config.type}`)
  return config
}

function remote(config: McpServerConfig) {
  if (config.type !== "remote") throw new Error(`expected a remote server, got ${config.type}`)
  return config
}

// The loader splits our own skill files, so a body that still carries frontmatter would leak
// metadata into the model context.
test("splitFrontmatter separates fields from the body", () => {
  const { fields, body } = splitFrontmatter('---\nname: demo\ndescription: "quoted"\n---\n\n# Body\n')
  assert.equal(fields.name, "demo")
  assert.equal(fields.description, "quoted")
  assert.equal(body, "# Body\n")
})

// Files without frontmatter must survive unchanged, so a reference or plain markdown never breaks.
test("splitFrontmatter keeps text without frontmatter", () => {
  const { fields, body } = splitFrontmatter("# Title\n")
  assert.deepEqual(fields, {})
  assert.equal(body, "# Title\n")
})

// A Windows checkout or a CRLF file must not carry carriage returns into the system prompt.
test("splitFrontmatter normalizes CRLF input", () => {
  const { fields, body } = splitFrontmatter("---\r\nname: demo\r\n---\r\n\r\n# Body\r\n")
  assert.equal(fields.name, "demo")
  assert.equal(body, "# Body\n")
})

// The always-on rules reach the system prompt in one piece: body plus every reference, in the
// order the skill links them, so the text matches what a portable client would read.
test("loadRules assembles body and references in link order", async () => {
  const rules = await loadRules(join(SKILLS, RULES_SKILL))

  assert.ok(!rules.startsWith("---"), "rules must not start with frontmatter")
  assert.match(rules, /Write in English/)

  const headings = ["# Planning", "# Logging", "# Security", "# Cleanup", "# Accessibility", "# Coding Rules"]
  const positions = headings.map((heading) => rules.indexOf(heading))
  for (const [index, position] of positions.entries()) {
    assert.ok(position !== -1, `missing reference ${headings[index]}`)
    if (index > 0) assert.ok(positions[index - 1] < position, `${headings[index]} is out of order`)
  }
})

// On-demand skills stay separate from the rules: rules are injected every call, skills are loaded
// when the model asks, and registering the rules skill twice would pay for the text twice.
test("loadSkills returns the on-demand skills without the rules skill", async () => {
  const skills = await loadSkills(SKILLS, [RULES_SKILL])

  assert.deepEqual(
    skills.map((skill) => skill.id),
    ["code-review", "docs-rules", "git-workflow"],
  )
  for (const skill of skills) {
    assert.ok(isAbsolute(skill.path), `${skill.id}: path must be absolute`)
    assert.ok(skill.path.endsWith("SKILL.md"), `${skill.id}: path must point at SKILL.md`)
    assert.ok(skill.description.length > 0, `${skill.id}: description must not be empty`)
    assert.ok(!skill.body.startsWith("---"), `${skill.id}: body must not contain frontmatter`)
  }
})

// The portable mcp.json is the only source for servers, so both transports have to map without
// leaving an unexpanded placeholder behind; `${PLUGIN_ROOT}` becomes the installed package path.
test("loadMcpServers maps both transports from mcp.json", async () => {
  const servers = await loadMcpServers(ROOT)
  const byName = new Map(servers.map((server) => [server.name, server.config]))

  const tools = local(byName.get("agent-tools")!)
  assert.equal(tools.command[0], "python3")
  assert.equal(tools.command[1], join(ROOT, "tools", "mcp_server.py"))
  assert.equal(tools.cwd, undefined)

  const context7 = remote(byName.get("context7")!)
  assert.equal(context7.url, "https://mcp.context7.com/mcp")

  assert.ok(!JSON.stringify(servers).includes("${"), "placeholders must be expanded")
})

// Windows ships `python` instead of `python3`, and a hard-coded interpreter name would make the
// work-log server fail to start there.
test("loadMcpServers replaces the python3 command when asked", async () => {
  const servers = await loadMcpServers(ROOT, { python: "python" })
  const tools = local(servers.find((server) => server.name === "agent-tools")!.config)
  assert.equal(tools.command[0], "python")
})

// One unusable entry must not take its siblings down: an entry that needs a writable plugin data
// directory is dropped, the rest still loads.
test("loadMcpServers skips an entry that needs PLUGIN_DATA", async () => {
  const dir = await mkdtemp(join(tmpdir(), "agent-config-"))
  try {
    await writeFile(
      join(dir, "mcp.json"),
      JSON.stringify({
        mcpServers: {
          keep: { type: "streamable-http", url: "https://example.com/mcp" },
          drop: { type: "stdio", command: "python3", args: ["${PLUGIN_DATA}/state.json"] },
        },
      }),
    )

    const servers = await loadMcpServers(dir)
    assert.deepEqual(
      servers.map((server) => server.name),
      ["keep"],
    )
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
})
