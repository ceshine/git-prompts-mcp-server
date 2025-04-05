# Git Prompts MCP Server

This repository provides a Model Context Protocol (MCP) server that offers several commands to generate prompts based on the Git repository's content.

(This repository draws heavy inspiration from [MarkItDown MCP server](https://github.com/KorigamiK/markitdown_mcp_server) and the example [Git MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/git).)


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
  - Note: This is largely the same as `/git-diff`, but it includes instructions for generating a pull request description at the end of the output.
3. `/git-cached-diff`: Populate the diff results for the staged changes and HEAD.

Examples:

1. `/generate-pr-desc main`
2. `/git-diff dev`
3. `/git-cached-diff`

## License

MIT License. See [LICENSE](LICENSE) for details.
