# agent-config

Global agent rules and a small MCP tool server, packaged as a portable
[Agent Plugin](https://agent-plugins.org). Load it into any client that supports
the Agent Plugins 1.0 format and your agentic engineering setup follows the same
baseline everywhere.

The plugin keeps global rules and helper tools in one versioned place, so
individual projects stay clean.

## What is in here

```
agent-config/
├── plugin.json                 # portable manifest
├── mcp.json                    # stdio MCP server + remote Context7 declaration
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

## Install

Register this repository as a plugin source in a client that supports the Agent
Plugins format. With the default branch:

```
github:anansio/agent-config
```

See the [Agent Plugins documentation](https://agent-plugins.org) for how to add
a source in your client.

## License

MIT. See [LICENSE](LICENSE).
