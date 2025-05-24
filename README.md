# Git Prompts MCP Server

This repository provides a Model Context Protocol (MCP) server that offers several commands to generate prompts based on the Git repository's content.

(This repository draws heavy inspiration from [MarkItDown MCP server](https://github.com/KorigamiK/markitdown_mcp_server) and the example [Git MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/git).)

Here's another MCP server project of mine: [ceshine/jira-prompts-mcp-server](https://github.com/ceshine/jira-prompts-mcp-server)

### 0.1.0

* Migrate from the low-level [mcp package](https://github.com/modelcontextprotocol/python-sdk) to the [FastMCP](https://github.com/jlowin/fastmcp?tab=readme-ov-file) package.
* Add a CLI for testing the server.

### 0.0.1

The initial release with two prompts implemented: `git-cached-diff`, `git-diff`, `generate-pr-desc`

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
  - Note: This is largely the same as `/git-diff`, but it includes instructions for generating a pull request description at the end of the output.
3. `/git-cached-diff`: Populate the diff results for the staged changes and HEAD.

Examples:

1. `/generate-pr-desc main`
2. `/git-diff dev`
3. `/git-cached-diff`


### Testing the server using the CLI

Prerequisities: configuring the required environment variables (`GIT_REPOSITORY`, `GIT_OUTPUT_FORMAT`, `GIT_EXCLUDES`)

You can quickly test the MCP server using the CLI. Below are some example commands:

* `uv run python -m git_prompts_mcp_server.cli git-diff main`
* `uv run python -m jira_prompts_mcp_server.cli git-cached-diff`
* `uv run python -m jira_prompts_mcp_server.cli generate-pr-desc main`


## License

MIT License. See [LICENSE](LICENSE) for details.
