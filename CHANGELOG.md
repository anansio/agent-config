# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `code-review` skill: a subagent reviews a change before it is done and writes
  its findings to `.agents/review.md` in the project.
- `global-rules` references for planning, logging, security, and cleanup.
- `kind` (`feature`, `fix`, `decision`) on the log tools, and a `kind` filter on
  `log_search`.
- Remote Context7 MCP server declaration in `mcp.json` (no credentials needed).

### Changed

- `global-rules` is now described as always-on, so clients that load a skill by
  its description still pick it up.

### Fixed

- Dropped `cwd` from the `agent-tools` MCP declaration, so the default work log
  lands in the project directory instead of the plugin directory.
- `docs-rules` no longer declares the non-portable `paths:` frontmatter field,
  which conforming clients reject by skipping the skill; activation now rests on
  its description.

## [0.1.0] - 2026-10-18

### Added

- Agent Plugin manifest and stdio MCP server declaration.
- Baseline skills: global rules, document rules, and a git workflow.
- Work-log MCP tools: `log_append`, `log_update`, `log_delete`, `log_search`.
- Test suite for the server and the plugin, run in CI on Python 3.10 to 3.13.
- MIT license.

[0.1.0]: https://github.com/anansio/agent-config/releases/tag/v0.1.0
