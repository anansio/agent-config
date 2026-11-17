/**
 * Work-log storage: JSON Lines file access, entry identifiers, and log locations.
 *
 * Entries are stored one per line so that appending stays O(1) and reading
 * streams the file instead of loading it, which keeps large logs cheap.
 */
import { randomBytes } from "node:crypto"
import { appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, isAbsolute, join, resolve, sep } from "node:path"
import { fileURLToPath } from "node:url"

// Default location, relative to the project the agent works in. Tools accept a
// project directory and an explicit path to place the log anywhere else.
export const DEFAULT_LOG_FILE = ".agents/log.jsonl"

// Where this repository is installed. A client that starts the server without a
// project working directory (OpenHands uses the plugin cache) must not log here.
export const PLUGIN_ROOT = resolve(fileURLToPath(new URL("../../", import.meta.url)))

// A client cannot tell the server which project it serves, so the agent passes
// `project_dir` per call. This variable covers a client that sets it once for the
// whole server process instead.
export const PROJECT_DIR_ENV = "AGENT_CONFIG_PROJECT_DIR"

function expandHome(value) {
  const trimmed = value.trim()
  return trimmed.startsWith("~") ? join(homedir(), trimmed.slice(1)) : trimmed
}

function isInside(child, parent) {
  return child === parent || child.startsWith(parent.endsWith(sep) ? parent : parent + sep)
}

// A base directory that is clearly not a project: writing there mixes every
// project's log into one file in the wrong place, and nothing reports it.
function wrongBase(dir) {
  if (isInside(dir, PLUGIN_ROOT)) return "the plugin install"
  if (dir === resolve(homedir())) return "your home directory"
  return undefined
}

/**
 * Return the directory the log belongs to: the `project_dir` argument, the
 * `AGENT_CONFIG_PROJECT_DIR` variable, or the server's working directory.
 *
 * A relative default silently depends on how the client started the server, so a
 * working directory that cannot be a project fails loudly instead.
 */
export function resolveProjectDir(projectDir) {
  const given = expandHome(projectDir ?? "") || expandHome(process.env[PROJECT_DIR_ENV] ?? "")
  if (given) return resolve(given)

  const cwd = process.cwd()
  const wrong = wrongBase(cwd)
  if (wrong) {
    throw new Error(
      `No project directory: this server runs in ${wrong} (${cwd}), not in a project. ` +
        "Pass project_dir with the directory you are working in.",
    )
  }
  return cwd
}

/**
 * Return the absolute log file to use. An absolute `path` is taken as is, a
 * relative one resolves against the project directory, and the default is
 * `.agents/log.jsonl` there.
 */
export function resolveLogPath({ path, projectDir } = {}) {
  const target = expandHome(path ?? "")
  if (target && isAbsolute(target)) return target
  if (target) return resolve(resolveProjectDir(projectDir), target)
  return join(resolveProjectDir(projectDir), DEFAULT_LOG_FILE)
}

/** Return a short random id used to reference an entry. */
export function newId() {
  return randomBytes(4).toString("hex")
}

/** Return the current UTC time as an ISO-8601 string with second precision. */
export function nowTs() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00")
}

/** Return every stored entry in file order. Missing file means no entries. */
export function readEntries(logPath) {
  if (!existsSync(logPath)) return []
  const entries = []
  for (const line of readFileSync(logPath, "utf8").split("\n")) {
    const trimmed = line.trim()
    if (trimmed) entries.push(JSON.parse(trimmed))
  }
  return entries
}

/** Append one entry as a single line. */
export function appendEntry(logPath, entry) {
  mkdirSync(dirname(logPath), { recursive: true })
  appendFileSync(logPath, JSON.stringify(entry) + "\n", "utf8")
}

/** Rewrite the log atomically, so a crash cannot leave a partial file. */
export function writeEntries(logPath, entries) {
  mkdirSync(dirname(logPath), { recursive: true })
  const tmp = logPath + ".tmp"
  writeFileSync(tmp, entries.map((entry) => JSON.stringify(entry) + "\n").join(""), "utf8")
  renameSync(tmp, logPath)
}
