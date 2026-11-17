/** The work-log tool group: append, update, delete, and search entries. */
import {
  appendEntry,
  newId,
  nowTs,
  readEntries,
  resolveLogPath,
  writeEntries,
} from "../log_store.js"

// Every tool takes `project_dir` for the project and `path` for the log file, so a
// project can keep its log wherever it likes. The wording is shared with the rules.
const PATH_DESCRIPTION =
  "Log file. An absolute path is used as is; a relative one resolves against project_dir. " +
  "Omit it to use '.agents/log.jsonl' in project_dir."

const PROJECT_DIR_DESCRIPTION =
  "Directory you are working in, the project root. Always pass it: the server cannot see the " +
  "project on its own, and without it the log can land in the plugin install."

const KIND_DESCRIPTION = "Optional category, for filtering: 'feature', 'fix', or 'decision'."

function requireString(args, key) {
  const value = args[key]
  if (typeof value !== "string") throw new TypeError(`'${key}' must be a string`)
  return value
}

/** Resolve the log file from `path` and `project_dir`, the two location arguments. */
function logPath(args) {
  return resolveLogPath({
    path: optionalString(args, "path"),
    projectDir: optionalString(args, "project_dir"),
  })
}

function optionalString(args, key) {
  const value = args[key]
  if (value === undefined || value === null) return undefined
  if (typeof value !== "string") throw new TypeError(`'${key}' must be a string`)
  return value
}

/** Append one work-log entry and return its id. */
export function append(args) {
  const text = requireString(args, "text")
  const file = logPath(args)
  const kind = optionalString(args, "kind")

  const entry = { id: newId(), ts: nowTs(), text }
  if (kind) entry.kind = kind
  appendEntry(file, entry)
  return entry.id
}

/** Replace the text of an existing entry, for a changed plan or wording. */
export function update(args) {
  const entryId = requireString(args, "entry_id")
  const text = requireString(args, "text")
  const file = logPath(args)
  const kind = optionalString(args, "kind")

  const entries = readEntries(file)
  const entry = entries.find((candidate) => candidate.id === entryId)
  if (!entry) throw new Error(`No log entry with id ${entryId}`)

  entry.text = text
  entry.ts = nowTs()
  if (kind) entry.kind = kind
  writeEntries(file, entries)
  return entryId
}

/** Remove one obsolete entry, so superseded steps do not clutter the log. */
export function remove(args) {
  const entryId = requireString(args, "entry_id")
  const file = logPath(args)

  const entries = readEntries(file)
  const remaining = entries.filter((entry) => entry.id !== entryId)
  if (remaining.length === entries.length) throw new Error(`No log entry with id ${entryId}`)

  writeEntries(file, remaining)
  return entryId
}

/**
 * Return matching entries as compact JSON. An empty query returns all.
 * A kind narrows the result to entries of that category.
 */
export function search(args) {
  const query = optionalString(args, "query") ?? ""
  const file = logPath(args)
  const kind = optionalString(args, "kind")

  const needle = query.toLowerCase()
  const matches = []
  for (const entry of readEntries(file)) {
    if (needle && !entry.text.toLowerCase().includes(needle)) continue
    if (kind && entry.kind !== kind) continue

    const result = { id: entry.id, ts: entry.ts, text: entry.text }
    if (entry.kind) result.kind = entry.kind
    matches.push(result)
  }
  return JSON.stringify(matches)
}

/** Tool specs registered by the server: MCP name -> description, schema, handler. */
export const SPECS = {
  log_append: {
    description:
      "Append a short work-log entry: a feature, a fix, or a decision. Record meaningful " +
      "milestones, not every step. Pass project_dir with the directory you are working in; the " +
      "entry lands in '.agents/log.jsonl' there unless a different path is given.",
    inputSchema: {
      type: "object",
      properties: {
        text: { type: "string", description: "Short entry: what was done and why." },
        kind: { type: "string", description: KIND_DESCRIPTION },
        path: { type: "string", description: PATH_DESCRIPTION },
        project_dir: { type: "string", description: PROJECT_DIR_DESCRIPTION },
      },
      required: ["text"],
    },
    handler: append,
  },
  log_update: {
    description:
      "Rewrite an existing entry by id. Use it when a course change makes a recorded step " +
      "obsolete or inaccurate, so the log stays consistent with the final approach. Pass the same " +
      "project_dir you logged with.",
    inputSchema: {
      type: "object",
      properties: {
        entry_id: { type: "string", description: "Entry id to rewrite." },
        text: { type: "string", description: "New entry text." },
        kind: { type: "string", description: KIND_DESCRIPTION },
        path: { type: "string", description: PATH_DESCRIPTION },
        project_dir: { type: "string", description: PROJECT_DIR_DESCRIPTION },
      },
      required: ["entry_id", "text"],
    },
    handler: update,
  },
  log_delete: {
    description:
      "Remove an entry by id. Use it to drop a step that turned out to be a dead end, so " +
      "abandoned back-and-forth does not accumulate. Pass the same project_dir you logged with.",
    inputSchema: {
      type: "object",
      properties: {
        entry_id: { type: "string", description: "Entry id to remove." },
        path: { type: "string", description: PATH_DESCRIPTION },
        project_dir: { type: "string", description: PROJECT_DIR_DESCRIPTION },
      },
      required: ["entry_id"],
    },
    handler: remove,
  },
  log_search: {
    description:
      "Search entries by substring and return them with their ids, to review the log or find " +
      "an entry to update or delete. A kind narrows the result to one category. Pass the same " +
      "project_dir you logged with.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Substring to match. Empty returns all entries." },
        kind: { type: "string", description: KIND_DESCRIPTION },
        path: { type: "string", description: PATH_DESCRIPTION },
        project_dir: { type: "string", description: PROJECT_DIR_DESCRIPTION },
      },
    },
    handler: search,
  },
}
