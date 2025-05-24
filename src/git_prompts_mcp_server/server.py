import os
import json
import logging
from fnmatch import fnmatch
from typing import cast

import git
from fastmcp import FastMCP
from pydantic import Field
from mcp.types import PromptMessage, TextContent

from .version import __version__

# Initialize server
APP = FastMCP(name="git_prompt_mcp_server")
LOGGER = logging.getLogger(__name__)


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


class GitMethodCollection:
    def __init__(self):
        repository = os.environ["GIT_REPOSITORY"]
        try:
            self.repo = git.Repo(repository)
        except git.InvalidGitRepositoryError:
            LOGGER.error(f"{repository} is not a valid Git repository")
            os.system(f"notify-send 'Git Prompts MCP server version {__version__} failed to start'")
            return

        self.excludes = os.environ["GIT_EXCLUDES"].split(",")
        self.json_format = os.environ["GIT_OUTPUT_FORMAT"].lower() == "json"

    async def generate_pr_desc_prompt(
        self, ancestor: str = Field(..., description="The ancestor commit hash or branch name")
    ) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        diff_results = _get_diff_results(self.repo.commit(ancestor), self.repo.head.commit, self.excludes)

        try:
            if self.json_format is True:
                diff_str = _format_diff_results_as_json(diff_results)
            else:
                diff_str = _format_diff_results_as_plain_text(diff_results)

            prompt_text = (
                diff_str
                + f"\n\nAbove is the diff results between HEAD and {ancestor} in {'the JSON format' if self.json_format else 'plain text'}.\n"
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

    async def git_diff_prompt(
        self, ancestor: str = Field(..., description="The ancestor commit hash or branch name")
    ) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        diff_results = _get_diff_results(self.repo.commit(ancestor), self.repo.head.commit, self.excludes)
        try:
            if self.json_format is True:
                diff_str = _format_diff_results_as_json(diff_results)
            else:
                diff_str = _format_diff_results_as_plain_text(diff_results)

            prompt_text = (
                diff_str
                + f"\n\nAbove is the diff results between HEAD and {ancestor} in {'the JSON format' if self.json_format else 'plain text'}.\n"
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

    async def git_cached_diff_prompt(self) -> PromptMessage:
        diff_results = _get_diff_results(self.repo.head.commit, None, self.excludes)
        try:
            if self.json_format is True:
                diff_str = _format_diff_results_as_json(diff_results)
            else:
                diff_str = _format_diff_results_as_plain_text(diff_results)

            prompt_text = (
                diff_str
                + f"\n\nAbove is the staged changes in {'the JSON format' if self.json_format else 'plain text'}."
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

    async def get_commit_messages_prompt(
        self, ancestor: str = Field(..., description="The ancestor commit hash or branch name")
    ) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        try:
            commits = list(self.repo.iter_commits(rev=f"{ancestor}..HEAD"))
            if not commits:
                commit_messages = f"No commits found between {ancestor} and HEAD."
            else:
                commit_messages = "\n".join([commit.message.strip() for commit in commits])
            
            prompt_text = (
                f"Commit messages between {ancestor} and HEAD:\n"
                + commit_messages
            )
            return PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=prompt_text,
                ),
            )
        except git.GitCommandError as e:
            raise ValueError(f"Error executing Git command: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error generating the final prompt for get-commit-messages: {str(e)}")


GIT_METHOD_COLLETION = GitMethodCollection()
APP.add_prompt(
    GIT_METHOD_COLLETION.generate_pr_desc_prompt,
    name="generate-pr-desc",
    description="Generate PR Description based on the diff between the HEAD and the ancestor branch or commit",
)
APP.add_prompt(
    GIT_METHOD_COLLETION.git_diff_prompt,
    name="git-diff",
    description="Generate a diff between the HEAD and the ancestor branch or commit",
)
APP.add_prompt(
    GIT_METHOD_COLLETION.git_cached_diff_prompt,
    name="git-cached-diff",
    description="Generate a diff between the files in the staging area (the index) and the HEAD",
)
APP.add_prompt(
    GIT_METHOD_COLLETION.get_commit_messages_prompt,
    name="get-commit-messages",
    description="Get commit messages between the ancestor and HEAD",
)
