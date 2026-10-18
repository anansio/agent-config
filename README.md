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
│   └── mcp_server.py           # stdlib-only MCP server, "hello" tool
├── README.md
└── LICENSE
```

## The MCP server

`tools/mcp_server.py` speaks MCP over stdio and uses only the Python standard
library, so it starts anywhere `python3` exists. It ships one tool:

- `hello` - returns a greeting. Use it to confirm the plugin is wired up.

Run it by hand to check it:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"hello","arguments":{"name":"you"}}}' \
  | python3 tools/mcp_server.py
```

Add more tools by extending the `TOOLS` mapping in that file.

## Install into OpenHands

Point OpenHands at this repository as a plugin source. With the default branch:

```
github:anansio/agent-config
```

See the OpenHands Agent Plugins documentation for the exact place to register a
source in your deployment.

## License

MIT. See [LICENSE](LICENSE).
