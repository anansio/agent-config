# agent-config

Global agent rules and a small MCP tool server, packaged as a portable
[Agent Plugin](https://agent-plugins.org). It loads into OpenHands and any other
client that supports the Agent Plugins 1.0 format.

The plugin keeps global rules and helper tools in one versioned place, so
individual projects stay clean.

## What is in here

```
agent-config/
├── plugin.json                 # portable manifest
├── mcp.json                    # stdio MCP server declaration
├── skills/
│   ├── global-rules/           # always-on baseline rules
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── accessibility.md
│   │       └── coding-rules.md
│   ├── docs-rules/             # path-triggered rule for document files
│   └── git-workflow/           # on-demand skill
├── tools/
│   └── mcp_server.py           # stdlib-only MCP server, work-log tools
├── tests/                      # server and plugin validation tests
├── .github/workflows/ci.yml    # runs the tests on push and pull request
├── README.md
└── LICENSE
```

## The MCP server

`tools/mcp_server.py` speaks MCP over stdio and uses only the Python standard
library, so it starts anywhere `python3` exists. It ships a small work-log tool
set. Entries are stored as JSON Lines in `.agent/log.jsonl` (one entry per
line), so appending stays O(1) and searching streams the file instead of loading
it. Override the location with the `AGENT_LOG_PATH` environment variable.

- `log_append` - add a short entry: what was done and why.
- `log_update` - rewrite an entry by id after a course change.
- `log_delete` - remove an entry that turned out to be a dead end.
- `log_search` - find entries by substring; returns them with their ids.

Run it by hand to check it:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"log_append","arguments":{"text":"verified the server"}}}' \
  | python3 tools/mcp_server.py
```

Add more tools by extending the `TOOLS` mapping in that file.

## Tests

The suite uses only the standard library:

```bash
python -m unittest discover -s tests -v
```

- `tests/test_mcp_server.py` covers the log tools and the stdio protocol loop.
- `tests/test_plugin.py` validates the plugin itself: the manifest, the MCP
  wiring, and each skill's frontmatter and relative links.

CI runs both on every push to `main` and every pull request, across Python
3.10 to 3.13.

## Install into OpenHands

Point OpenHands at this repository as a plugin source. With the default branch:

```
github:anansio/agent-config
```

See the OpenHands Agent Plugins documentation for the exact place to register a
source in your deployment.

## License

MIT. See [LICENSE](LICENSE).
