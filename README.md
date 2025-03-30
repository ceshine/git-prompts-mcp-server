# Git Prompts MCP Server

This repository provides a Model Context Protocol (MCP) server that offers several commands to generate prompts based on the Git repository's content.

(This repository draws heavy inspiration from [MarkItDown MCP server](https://github.com/KorigamiK/markitdown_mcp_server) and the example [Git MCP server](https://github.com/KorigamiK/git_mcp_server).)


## Installation

### Manual Installation

1. Clone this repository
2. Install dependencies: `uv sync --frozen`


## Usage

### As a MCP Server for Zed Editor

Add the following to your `settings.json`:

```json
"context_servers": {
  "git_prompt_mcp": {
    "command": {
      "path": "uv",
      "args": [
        "--directory",
        "/path/to/local/git_prompts_mcp_server",
        "run",
        "git-prompts-mcp-server",
        "/path/to/repo/", // parent folder of the .git directory
        "--excludes", // exclude files and directories from diff results
        "**/uv.lock",
        "--excludes",
        "**/.gitignore",
        "--format", // format for diff results
        "json"  // Options: json, text
      ]
    },
    "settings": {}
  }
}
```

#### Commands

The server responds to the following commands:

- `/generate-pr-desc <ancestor_branch_or_commit>`: Generate PR Description based on the diff between the HEAD and the ancestor branch or commit.

Example:

```bash
/generate-pr-desc main
```

## License

MIT License. See [LICENSE](LICENSE) for details.
