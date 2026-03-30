---
name: add-git-tools-mcp
description: Add the `git_tools` MCP server to a repository-local Codex config. Use when Codex needs to create or update `.codex/config.toml` in the current repository so the local config launches `git-prompts-mcp-server` via `uvx` with the repository root as an argument.
---

# Add Git Tools Mcp

## Overview

Update the repository-local `.codex/config.toml` so Codex can start the `git_tools` MCP server for the current repository. Create the config file if it does not exist, and preserve unrelated existing config.

## Workflow

1. Resolve the repository root from the current working directory and convert it to an absolute path.
2. Inspect `.codex/config.toml` under that repository root.
3. Create the file if it does not exist yet.
4. Add or update this TOML block, replacing the path argument with the absolute repository path:

```toml
[mcp_servers.git_tools]
command = "uvx"
args = [
  "--from",
  "git+https://github.com/ceshine/git-prompts-mcp-server.git",
  "git-prompts-mcp-server",
  "/absolute/path/to/repository",
  "--excludes",
  "**/*.lock",
  "--format",
  "json"
]
```

5. Preserve valid TOML formatting and avoid removing unrelated sections.
6. If an existing `mcp_servers.git_tools` block is present, replace it instead of creating a duplicate.

## Notes

- Prefer editing the local repository config at `.codex/config.toml`, not a global Codex config.
- Use the repository root path, not the `.codex` directory path, as the server argument.
- Keep the `**/*.lock` exclude and `json` format arguments intact unless the user explicitly asks to change them.
