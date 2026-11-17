import { readdir, readFile } from "node:fs/promises"
import { join, resolve } from "node:path"

export const RULES_SKILL = "global-rules"

export interface SkillSource {
  id: string
  name: string
  description: string
  path: string
  body: string
}

export type McpServerConfig =
  | {
      type: "local"
      command: string[]
      cwd?: string
      environment?: Record<string, string>
    }
  | {
      type: "remote"
      url: string
      headers?: Record<string, string>
    }

export interface McpServerEntry {
  name: string
  config: McpServerConfig
}

export interface Frontmatter {
  fields: Record<string, string>
  body: string
}

/** Split YAML frontmatter from the body. Values stay untyped strings: skills only declare scalars. */
export function splitFrontmatter(text: string): Frontmatter {
  const normalized = text.replace(/\r\n/g, "\n")
  if (!normalized.startsWith("---\n")) return { fields: {}, body: normalized }

  const end = normalized.indexOf("\n---", 3)
  if (end === -1) return { fields: {}, body: normalized }

  const fields: Record<string, string> = {}
  for (const line of normalized.slice(4, end).split("\n")) {
    const match = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(line)
    if (match) fields[match[1]] = match[2].trim().replace(/^["']|["']$/g, "")
  }
  return { fields, body: normalized.slice(end + 4).replace(/^\n+/, "") }
}

/**
 * Assemble the always-on rules from the `global-rules` skill: the SKILL.md body followed by
 * every reference it links, in link order, then any unlinked reference by name.
 */
export async function loadRules(skillDir: string): Promise<string> {
  const { body } = splitFrontmatter(await readFile(join(skillDir, "SKILL.md"), "utf8"))
  const referencesDir = join(skillDir, "references")

  let files: string[]
  try {
    files = (await readdir(referencesDir)).filter((name) => name.endsWith(".md"))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return body.trim()
    throw error
  }

  // The References section carries the intended reading order; links elsewhere in the body only
  // fill gaps, so a passing mention cannot move a reference to the front.
  const links = (text: string) =>
    [...text.matchAll(/\]\(references\/([^)]+)\)/g)].map((match) => match[1])
  const index = /## References\n([\s\S]*)$/.exec(body)?.[1] ?? ""
  const ordered = [...new Set([...links(index), ...links(body)].filter((name) => files.includes(name)))]
  for (const name of files.sort()) {
    if (!ordered.includes(name)) ordered.push(name)
  }

  const sections = await Promise.all(
    ordered.map(async (name) =>
      (await readFile(join(referencesDir, name), "utf8")).replace(/\r\n/g, "\n").trim(),
    ),
  )
  return [body.trim(), ...sections].join("\n\n")
}

/** Load on-demand skills from the portable `skills/` directory, skipping the rules skill. */
export async function loadSkills(
  skillsDir: string,
  exclude: readonly string[] = [],
): Promise<SkillSource[]> {
  const entries = await readdir(skillsDir, { withFileTypes: true })
  const ids = entries
    .filter((entry) => entry.isDirectory() && !exclude.includes(entry.name))
    .map((entry) => entry.name)
    .sort()

  const skills: SkillSource[] = []
  for (const id of ids) {
    const path = resolve(skillsDir, id, "SKILL.md")
    let text: string
    try {
      text = await readFile(path, "utf8")
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") continue
      throw error
    }

    const { fields, body } = splitFrontmatter(text)
    // A skill without a name or description is not portable, so clients skip it; registration does the same.
    if (!fields.name || !fields.description) continue
    skills.push({ id, name: fields.name, description: fields.description, path, body })
  }
  return skills
}

/**
 * Map the portable `mcp.json` to OpenCode server configurations.
 *
 * `${PLUGIN_ROOT}` resolves against the installed package. An entry that needs `${PLUGIN_DATA}`
 * is skipped: this plugin has no writable per-plugin data directory, and a broken entry must not
 * take its siblings down.
 */
export async function loadMcpServers(
  pluginRoot: string,
  options: { python?: string } = {},
): Promise<McpServerEntry[]> {
  const document = JSON.parse(await readFile(join(pluginRoot, "mcp.json"), "utf8")) as {
    mcpServers?: Record<string, Record<string, unknown>>
  }

  const entries = Object.entries(document.mcpServers ?? {}).sort(([a], [b]) => a.localeCompare(b))
  const servers: McpServerEntry[] = []
  for (const [name, entry] of entries) {
    const config = toOpenCodeServer(entry, pluginRoot, options.python)
    if (config) servers.push({ name, config })
  }
  return servers
}

function toOpenCodeServer(
  entry: Record<string, unknown>,
  pluginRoot: string,
  python: string | undefined,
): McpServerConfig | undefined {
  const type = entry.type

  if (type === "stdio") {
    if (typeof entry.command !== "string") return undefined

    const args = asStrings(entry.args).map((arg) => expand(arg, pluginRoot))
    const cwd = typeof entry.cwd === "string" ? expandPath(entry.cwd, pluginRoot) : undefined
    const environment = expandEnv(entry.env, pluginRoot)
    if (needsPluginData([...args, ...Object.values(environment), ...(cwd ? [cwd] : [])])) {
      return undefined
    }

    const command = entry.command === "python3" && python ? python : entry.command
    return {
      type: "local",
      command: [resolveCommand(command, pluginRoot), ...args],
      ...(cwd ? { cwd } : {}),
      ...(Object.keys(environment).length > 0 ? { environment } : {}),
    }
  }

  if (type === "streamable-http" || type === "sse") {
    if (typeof entry.url !== "string") return undefined
    const headers = literalHeaders(entry.headers)
    return { type: "remote", url: entry.url, ...(headers ? { headers } : {}) }
  }

  return undefined
}

function asStrings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []
}

function expand(value: string, pluginRoot: string): string {
  return value.replace(/\$\{PLUGIN_ROOT\}/g, pluginRoot)
}

function expandPath(value: string, pluginRoot: string): string {
  const expanded = expand(value, pluginRoot)
  return expanded.startsWith("./") ? resolve(pluginRoot, expanded) : expanded
}

function resolveCommand(command: string, pluginRoot: string): string {
  return command.startsWith("./") ? resolve(pluginRoot, command) : command
}

function expandEnv(value: unknown, pluginRoot: string): Record<string, string> {
  return stringRecord(value, (raw) => expand(raw, pluginRoot))
}

// Configured headers are literal package data: the portable format does not expand them.
function literalHeaders(value: unknown): Record<string, string> | undefined {
  const headers = stringRecord(value)
  return Object.keys(headers).length > 0 ? headers : undefined
}

function stringRecord(value: unknown, map: (raw: string) => string = (raw) => raw) {
  const record: Record<string, string> = {}
  if (!value || typeof value !== "object") return record
  for (const [key, raw] of Object.entries(value)) {
    if (typeof raw === "string") record[key] = map(raw)
  }
  return record
}

function needsPluginData(values: readonly string[]): boolean {
  return values.some((value) => value.includes("${PLUGIN_DATA}"))
}
