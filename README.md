# Git Prompts MCP Server

This repository provides a Model Context Protocol (MCP) server that offers several commands to generate prompts based on the Git repository's content.

[![Tests](https://github.com/ceshine/git-prompts-mcp-server/actions/workflows/run_tests.yml/badge.svg)](https://github.com/ceshine/git-prompts-mcp-server/actions/workflows/run_tests.yml)

<p>
  <a href="https://glama.ai/mcp/servers/@ceshine/git-prompts-mcp-server">
    <img width="380" height="200" src="https://glama.ai/mcp/servers/@ceshine/git-prompts-mcp-server/badge" alt="Git Prompts Server MCP server" />
  </a>
</p>

<p>
  <a href="https://mseep.ai/app/ceshine-git-prompts-mcp-server">
    <img width="380" height="132" src="https://mseep.net/pr/ceshine-git-prompts-mcp-server-badge.png" alt="MseeP.ai Security Assessment Badge" />
  </a>
</p>

## Acknowledgements

- This repository draws heavy inspiration from [MarkItDown MCP server](https://github.com/KorigamiK/markitdown_mcp_server) and the example [Git MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/git).
- The [AGENTS.md](./AGENTS.md) was adapted from the example sin this blog post: [Getting Good Results from Claude Code](https://www.dzombak.com/blog/2025/08/getting-good-results-from-claude-code/).

## Usage

Prerequisites: Python 3.12+ and [uv](https://github.com/astral-sh/uv)

### As a MCP Server for Zed Editor

Add the following to your `settings.json`:

```json
"context_servers": {
  "git_prompt_mcp": {
    "command": "uvx",
    "args": [
      "--from",
      "git+https://github.com/ceshine/git-prompts-mcp-server.git",
      "git-prompts-mcp-server",
      "/path/to/repo/", // parent folder of the .git directory
      "--excludes", // Exclude files and directories from diff results (the server uses pathlib.PurePath behind the scenes)
      "**/uv.lock",
      "--format", // format for diff results
      "json"  // options: json, text
    ],
    "env": {}
  }
}
```

### As a Gemini CLI Extension

To enable the commands and tools provided by this server in your Gemini CLI:

1.  **Install the extension:**
    ```bash
    gemini extension install https://github.com/ceshine/git-prompts-mcp-server.git --auto-update
    ```
    This command will install the `git-prompts-mcp-server` as a Gemini CLI extension, making its prompts and tools available for use.
2.  **Usage:**
    Once installed, the prompts (e.g., `/git-diff`, `/generate-pr-desc`) and tools (e.g., `git_diff`, `git_cached_diff`) will be automatically available to your Gemini CLI sessions when run within a Git repository.


**Important Caveat:** This extension relies on the current working directory being part of a Git repository (i.e., containing a `.git` subfolder). If the Gemini CLI is not run from the root of a Git project, the extension's commands and tools may not function as expected.


#### Commands

The server responds to the following commands:

1. `/git-diff <ancestor_branch_or_commit>`: Populate the diff results between HEAD and the specified ancestor branch or commit.
2. `/generate-pr-desc <ancestor_branch_or_commit>`: Generate a pull request description based on the diff results and commit history between HEAD and the specified ancestor branch or commit.
3. `/git-cached-diff`: Populate the diff results for the staged changes and HEAD.
4. `/git-commit-messages <ancestor_branch_or_commit>`: Get commit messages between the ancestor and HEAD.
5. `/generate-commit-message [num_commits]`: Generate commit message based on the diff between the files in the staging area (the index) and the HEAD. Additionally, it points out any potential issues in the changes at the end of the output. `num_commits` defaults to 5. Set to 0 to exclude commit history.

Examples:

1. `/generate-pr-desc main`
2. `/git-diff dev`
3. `/git-cached-diff`
4. `/git-commit-messages main`
5. `/generate-commit-message` or `/generate-commit-message 3`

#### Tools

The server also provides the following tools for MCP-compatible clients:

- `git-diff`: Get a diff between the HEAD and the ancestor branch or commit.
- `git-cached-diff`: Get a diff between the files in the staging area (the index) and the HEAD.
- `git-commit-messages`: Get commit messages between the ancestor and HEAD.

#### Environment Variables

The server can be configured with the following environment variables, which can be set in the `env` section of the Zed `settings.json`:

- `GIT_REPOSITORY`: The path to the Git repository. This is automatically passed by Zed.
- `GIT_EXCLUDES`: A comma-separated list of file patterns to exclude from the diff results (e.g., `"*/uv.lock,*.log"`).
- `GIT_OUTPUT_FORMAT`: The output format for the diff results. Can be `json` (default) or `text`.

## Development

1. Clone this repository
2. Install dependencies: `uv sync --frozen`

## Release Notes

### 0.3.2 (2026-01-02)

- **Updated FastMCP prompt argument type hints to use `Annotated[..., Field(...)]`, so FastMCP correctly applies defaults when the client does not provide values for optional arguments.**
- Added a new CLI command `prompt-generate-commit-message` to generate commit messages via the `/generate-commit-message` prompt, with optional `--num-commits`.
- Fixed a typo by renaming `GIT_METHOD_COLLETION` to `GIT_METHOD_COLLECTION`, and added logging plus validation to reject negative `num_commits`.

### 0.3.1 (2025-12-10)

- Added a new prompt `/generate-commit-message` to generate commit messages based on staged changes and recent commit history. It also highlights potential issues in the changes.
- Added `gemini-extension.json` to support direct installation as a Gemini CLI extension.
- Added support for `.pre-commit-config.yaml` for development.

### 0.3.0 (2025-09-05)

- Implemented the MCP tool version of the three MCP prompts: `git-diff`, `generate-pr-desc`, and `git-cached-diff`. This allows for a more integrated experience with MCP-compatible clients.
- Added a new command `/git-commit-messages` to get commit messages between a specified ancestor and HEAD.

## License

MIT License. See [LICENSE](LICENSE) for details.
