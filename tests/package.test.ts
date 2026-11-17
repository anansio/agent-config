import assert from "node:assert/strict"
import { execFile } from "node:child_process"
import { resolve } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import { promisify } from "node:util"

const run = promisify(execFile)
const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)))

// `opencode plugin add` installs this repository as a package, so anything the plugin reads at
// runtime has to pass the `files` allowlist. A missing entry only shows up on a user's machine.
test("the package payload contains everything the plugin reads at runtime", async () => {
  const npm = process.platform === "win32" ? "npm.cmd" : "npm"
  const { stdout } = await run(npm, ["pack", "--dry-run", "--json"], {
    cwd: ROOT,
    maxBuffer: 10 * 1024 * 1024,
  })

  // npm 11 returns an array of pack results, npm 12 a map keyed by package name.
  const parsed = JSON.parse(stdout)
  const pack = Array.isArray(parsed) ? parsed[0] : Object.values(parsed)[0]
  const paths = new Set(
    (pack as { files: { path: string }[] }).files.map((file) => file.path),
  )

  for (const required of [
    "package.json",
    "mcp.json",
    "opencode/index.ts",
    "opencode/lib.ts",
    "skills/global-rules/SKILL.md",
    "skills/global-rules/references/planning.md",
    "skills/code-review/SKILL.md",
    "tools/mcp_server.js",
    "tools/agent_mcp/server.js",
    "tools/agent_mcp/log_store.js",
    "tools/agent_mcp/tools/log.js",
  ]) {
    assert.ok(paths.has(required), `package is missing ${required}`)
  }

  // Tests and CI config stay out of the installed package; they add weight and no runtime value.
  assert.ok(![...paths].some((path) => path.startsWith("tests/")), "tests must not ship")
})
