# agent-config

Global agent rules and a small MCP tool server, packaged as a portable
[Agent Plugin](https://agent-plugins.org). Load it into any client that supports
the Agent Plugins 1.0 format and your agentic engineering setup follows the same
baseline everywhere.

The same repository is an [OpenCode](https://opencode.ai) 2.3+ plugin package. It
reads the portable files at load time and registers them with OpenCode, so both
install paths share one source and no content is duplicated.

The plugin keeps global rules and helper tools in one versioned place, so
individual projects stay clean.

## What is in here

```
agent-config/
├── plugin.json                 # portable manifest
├── mcp.json                    # stdio MCP server + remote Context7 declaration
├── package.json                # OpenCode plugin package, installed from git
├── opencode/
│   ├── index.ts                # OpenCode 2.x registration
│   └── lib.ts                  # reads the portable package at load time
├── skills/
│   ├── global-rules/           # always-on baseline rules
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── accessibility.md
│   │       ├── cleanup.md
│   │       ├── coding-rules.md
│   │       ├── logging.md
│   │       ├── planning.md
│   │       └── security.md
│   ├── code-review/            # on-demand skill: subagent review gate
│   ├── docs-rules/             # on-demand skill for documentation
│   └── git-workflow/           # on-demand skill
├── tools/
│   ├── mcp_server.py           # stdio entry point (thin launcher)
│   └── agent_mcp/              # server package
│       ├── server.py           # JSON-RPC loop and tool registry
│       ├── log_store.py        # JSON Lines storage and entry ids
│       └── tools/              # one module per tool group
│           └── log.py
├── tests/                      # server and plugin validation tests
├── .github/workflows/ci.yml    # runs the tests on push and pull request
├── README.md
├── CHANGELOG.md
├── SECURITY.md
└── LICENSE
```

## Skills

`global-rules` is meant to be loaded always: its description says so, so a
client that only loads a skill by its description still picks it up. It points
at the bundled references for planning, logging, security, cleanup,
accessibility, and coding. `code-review`, `docs-rules`, and `git-workflow` load
on demand from their descriptions.

The rules stay in the portable skill format so every Agent Plugins client can
read them. OpenCode does not receive them as a skill: the plugin reads the skill
body and its references and adds them to the system prompt of every model call.
That is what "always on" means in OpenCode, and registering the same text as a
skill as well would pay for it twice.

## The MCP server

The server lives in the `tools/agent_mcp/` package: `server.py` holds the
JSON-RPC loop and the tool registry, `log_store.py` owns storage, and each tool
group is its own module under `tools/agent_mcp/tools/`. `tools/mcp_server.py`
is a thin stdio entry point. It uses only the Python standard library, so it
starts anywhere `python3` exists.

Entries are stored as JSON Lines (one entry per line) with an id and a UTC
timestamp, so appending stays O(1) and searching streams the file instead of
loading it.

By default the log is written to `.agents/log.jsonl` in the project directory.
Every tool also takes an optional `path`, so a project can keep its log wherever
it likes. The file is plain text and can be committed with the project if you
want the work history to travel with it.

- `log_append` - add a short entry: what was done and why, with an optional
  `kind` (`feature`, `fix`, `decision`).
- `log_update` - rewrite an entry by id after a course change, and recategorize
  it with an optional `kind`.
- `log_delete` - remove an entry that turned out to be a dead end.
- `log_search` - find entries by substring or `kind`; returns them with their
  ids.

Add more tools by extending the specs in the relevant group module under
`tools/agent_mcp/tools/`, then importing that group in `server.py`.

## MCP servers

`mcp.json` declares two servers:

- `agent-tools` - this repository's stdio server, bundled with the plugin.
- `context7` - the remote [Context7](https://context7.com) docs server at
  `https://mcp.context7.com/mcp`. It needs no credentials; an optional API key
  only raises rate limits and is a client-side concern, so it is not declared
  here.

Anything requiring a secret (an API key or token) belongs in the client, not in
the plugin: the Agent Plugins format has no portable credential field, and
OpenHands' loader reads `mcp.json` literally, without `${VAR}` expansion.

## Tests

The suite uses only the standard library:

```bash
python -m unittest discover -s tests -v
```

- `tests/test_mcp_server.py` covers the log tools, including a full stdio
  round trip with a real tool call.
- `tests/test_plugin.py` validates the plugin itself: the manifest, the MCP
  wiring (it starts the declared server), and each skill's frontmatter and
  relative links.

CI runs the suite on every push to `main` and every pull request, across Python
3.10 to 3.13.

The OpenCode plugin has its own suite. It needs Node 24 and no dependencies:

```bash
node --test tests/*.test.ts
```

- `tests/opencode.test.ts` runs the loader against this repository's files:
  frontmatter handling, rules assembly and order, the skills it registers, and
  the `mcp.json` mapping.
- `tests/package.test.ts` runs `npm pack --dry-run` and fails when the `files`
  allowlist misses something the plugin reads at runtime.

CI runs both suites on every push to `main` and every pull request.

## OpenCode

`opencode/index.ts` is an OpenCode 2.3+ server plugin. It reads the portable
package at load time and registers its contents:

- the `global-rules` text as a system prompt part for every model call in the
  agent loop, built from the skill body plus its references in the order the
  References section lists them;
- `code-review`, `docs-rules`, and `git-workflow` as skills, with the body
  inline and `path` pointing at the bundled `SKILL.md`, so their relative links
  resolve;
- the servers from `mcp.json`, with `${PLUGIN_ROOT}` resolved to the installed
  package. An entry that needs `${PLUGIN_DATA}` is skipped: this plugin has no
  writable data directory, and one bad entry does not stop its siblings.

`code-review` stays a skill. OpenCode 2.x plugins cannot register agents, so the
skill keeps its instruction to hand the review to a subagent instead of shipping
a dedicated agent definition.

The plugin needs OpenCode 2.3 or newer: it is built against `@opencode/plugin`
2.3, the version that ships with that release. Version 1 uses a different plugin
API.

## Install

### OpenHands and other Agent Plugins clients

Register this repository as a plugin source in a client that supports the Agent
Plugins format. With the default branch:

```
github:anansio/agent-config
```

See the [Agent Plugins documentation](https://agent-plugins.org) for how to add
a source in your client.

### OpenCode

Install the package from the repository, pinned to a release tag:

```bash
opencode plugin add github:anansio/agent-config#v0.2.0
opencode plugin list
```

The command manages the global OpenCode configuration. `opencode plugin update`
moves the package to the ref named in the configuration, and
`opencode plugin remove agent-config@0.2.0` removes it.

For project-local use, point the project configuration at a checkout:

```jsonc
{
  "plugins": ["./agent-config"],
}
```

## License

MIT. See [LICENSE](LICENSE).
