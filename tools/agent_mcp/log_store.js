/**
 * Work-log storage: JSON Lines file access and entry identifiers.
 *
 * Entries are stored one per line so that appending stays O(1) and reading
 * streams the file instead of loading it, which keeps large logs cheap.
 */
import { randomBytes } from "node:crypto"
import { appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join } from "node:path"

// Default location, relative to the project the agent works in. Tools accept an
// explicit path to place the log anywhere else.
export const DEFAULT_LOG_PATH = ".agents/log.jsonl"

/** Return the log file to use: the given path, or the project default. */
export function resolveLogPath(path) {
  if (!path) return DEFAULT_LOG_PATH
  return path.startsWith("~") ? join(homedir(), path.slice(1)) : path
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
