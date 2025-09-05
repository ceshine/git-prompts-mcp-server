# Git Prompts MCP Server

This repository provides a Model Context Protocol (MCP) server that offers several commands to generate prompts based on the Git repository's content.

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/ceshine-git-prompts-mcp-server-badge.png)](https://mseep.ai/app/ceshine-git-prompts-mcp-server)

[![Tests](https://github.com/ceshine/git-prompts-mcp-server/actions/workflows/run_tests.yml/badge.svg)](https://github.com/ceshine/git-prompts-mcp-server/actions/workflows/run_tests.yml)

## Acknowledgements

- This repository draws heavy inspiration from [MarkItDown MCP server](https://github.com/KorigamiK/markitdown_mcp_server) and the example [Git MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/git).
- The [AGENTS.md](./AGENTS.md) was adapted from the example sin this blog post: [Getting Good Results from Claude Code](https://www.dzombak.com/blog/2025/08/getting-good-results-from-claude-code/).

## Installation

### Manual Installation

1. Clone this repository
2. Install dependencies: `uv sync --frozen`

## Usage

### As a MCP Server for Zed Editor

Add the following to your `settings.json`:

#### Since Zed version 0.194.3

* Source of the change: "Use standardised format for configuring MCP Servers" ([#33539](https://github.com/zed-industries/zed/pull/33539))

```json
"context_servers": {
  "git_prompt_mcp": {
    "source": "custom",
    "command": "uv",
    "args": [
    "--directory",
    "/path/to/local/git_prompts_mcp_server",
    "run",
    "git-prompts-mcp-server",
    "/path/to/repo/", // parent folder of the .git directory
    "--excludes", // exclude files and directories from diff results (the server use fnmatch in the backend)
    "*/uv.lock",
    "--excludes",
    "uv.lock",
    "--excludes",
    ".gitignore",
    "--format", // format for diff results
    "json"  // options: json, text
    ],
    "env": {}
  }
}
```

#### Prior to Zed version 0.194.3

```json
"context_servers": {
  "git_prompt_mcp": {
    "source": "custom",  // This is required for Zed version 0.193.x.
    "command": {
      "path": "uv",
      "args": [
        "--directory",
        "/path/to/local/git_prompts_mcp_server",
        "run",
        "git-prompts-mcp-server",
        "/path/to/repo/", // parent folder of the .git directory
        "--excludes", // exclude files and directories from diff results (the server use fnmatch in the backend)
        "*/uv.lock",
        "--excludes",
        "uv.lock",
        "--excludes",
        ".gitignore",
        "--format", // format for diff results
        "json"  // options: json, text
      ]
    },
    "settings": {}
  }
}
```

#### Commands

The server responds to the following commands:

1. `/git-diff <ancestor_branch_or_commit>`: Populate the diff results between HEAD and the specified ancestor branch or commit.
2. `/generate-pr-desc <ancestor_branch_or_commit>`: Generate a pull request description based on the diff results between HEAD and the specified ancestor branch or commit.
  a.  Note: This is largely the same as `/git-diff`, but it includes instructions for generating a pull request description at the end of the output.
3. `/git-cached-diff`: Populate the diff results for the staged changes and HEAD.

Examples:

1. `/generate-pr-desc main`
2. `/git-diff dev`
3. `/git-cached-diff`

## Release Notes

### 0.3.0 (2025-09-05)

- Implemented the MCP tool version of the three MCP prompts: `git-diff`, `generate-pr-desc`, and `git-cached-diff`. This allows for a more integrated experience with MCP-compatible clients.

## License

MIT License. See [LICENSE](LICENSE) for details.
