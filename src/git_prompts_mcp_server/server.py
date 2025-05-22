import os
import json
import logging
from fnmatch import fnmatch
from pathlib import Path
from typing import cast

import git
from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage, TextContent

from .version import __version__

# Helper functions remain the same
def _format_diff_results_as_plain_text(diff_results: list[git.Diff]) -> str:
    return "\n".join(
        [
            f"File: {item.a_path or 'New Addition'} -> {item.b_path or 'Deleted'}\n"
            + ("-" * 50)
            + "\n"
            + cast(bytes, item.diff).decode("utf-8")
            + ("=" * 50)
            + "\n"
            for item in diff_results
        ]
    )


def _format_diff_results_as_json(diff_results: list[git.Diff]) -> str:
    return json.dumps(
        [
            {
                "a_path": item.a_path or "New Addition",
                "b_path": item.b_path or "Deleted",
                "diff": cast(bytes, item.diff).decode("utf-8"),
            }
            for item in diff_results
        ],
        indent=2,
        ensure_ascii=False,
    )


def _get_diff_results(
    source_commit: git.Commit, target_commit: git.Commit | None, excludes: list[str]
) -> list[git.Diff]:
    if target_commit is None:
        # Note: source_commit.diff() compares source with the index (staged changes)
        #       source_commit.diff(None) compares source with the working tree
        diff_results = source_commit.diff(create_patch=True)
    else:
        diff_results = source_commit.diff(target_commit, create_patch=True)

    for exclude_pattern in excludes:
        diff_results = [
            item
            for item in diff_results
            if not fnmatch(item.a_path or "", exclude_pattern) and not fnmatch(item.b_path or "", exclude_pattern)
        ]
    return diff_results


async def run(repository: Path, excludes: list[str] = [], json_format: bool = True):
    logger = logging.getLogger(__name__)

    try:
        repo = git.Repo(repository)
    except git.InvalidGitRepositoryError:
        logger.error(f"{repository} is not a valid Git repository")
        os.system("notify-send 'Git Prompts MCP server failed to start'")
        return

    # Initialize server
    app = FastMCP(name="git_prompt_mcp_server")

    @app.prompt(
        name="generate-pr-desc",
        description="Generate PR Description based on the diff between the HEAD and the ancestor branch or commit",
    )
    async def generate_pr_desc_prompt(ancestor: str) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        diff_results = _get_diff_results(repo.commit(ancestor), repo.head.commit, excludes)

        try:
            if json_format is True:
                diff_str = _format_diff_results_as_json(diff_results)
            else:
                diff_str = _format_diff_results_as_plain_text(diff_results)

            prompt_text = (
                diff_str
                + f"\n\nAbove is the diff results between HEAD and {ancestor} in {'the JSON format' if json_format else 'plain text'}.\n"
                + (
                    "\nPlease provide a detailed description of the above changes proposed by a pull request. "
                    "Your description should include, but is not limited to, the following sections:\n\n"
                    "- **Overview of the Changes:** A concise summary of what was modified.\n"
                    "- **Key Changes:** A list of the main changes that were implemented.\n"
                    "- (Only include when applicable) **New Dependencies Added:** Identify any new dependencies that have been introduced.\n"
                )
            )
            return PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=prompt_text,
                ),
            )
        except Exception as e:
            raise ValueError(f"Error generating the final prompt for generate-pr-desc: {str(e)}")

    @app.prompt(
        name="git-diff",
        description="Generate a diff between the HEAD and the ancestor branch or commit",
    )
    async def git_diff_prompt(ancestor: str) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        diff_results = _get_diff_results(repo.commit(ancestor), repo.head.commit, excludes)
        try:
            if json_format is True:
                diff_str = _format_diff_results_as_json(diff_results)
            else:
                diff_str = _format_diff_results_as_plain_text(diff_results)

            prompt_text = (
                diff_str
                + f"\n\nAbove is the diff results between HEAD and {ancestor} in {'the JSON format' if json_format else 'plain text'}.\n"
            )
            return PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=prompt_text,
                ),
            )
        except Exception as e:
            raise ValueError(f"Error generating the final prompt for git-diff: {str(e)}")

    @app.prompt(
        name="git-cached-diff",
        description="Generate a diff between the files in the staging area (the index) and the HEAD",
    )
    async def git_cached_diff_prompt() -> PromptMessage:
        diff_results = _get_diff_results(repo.head.commit, None, excludes)
        try:
            if json_format is True:
                diff_str = _format_diff_results_as_json(diff_results)
            else:
                diff_str = _format_diff_results_as_plain_text(diff_results)

            prompt_text = (
                diff_str
                + f"\n\nAbove is the staged changes in {'the JSON format' if json_format else 'plain text'}."
            )
            return PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=prompt_text,
                ),
            )
        except Exception as e:
            raise ValueError(f"Error generating the final prompt for git-cached-diff: {str(e)}")

    # FastMCP.run() uses stdio transport by default.
    # Server name is set in the FastMCP constructor.
    # Server version is not explicitly passed to run() in fastmcp.
    await app.run()
