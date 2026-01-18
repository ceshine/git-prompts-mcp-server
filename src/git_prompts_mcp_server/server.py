import os
import json
import logging
from pathlib import PurePath
from datetime import timezone
from typing import cast, Annotated

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


def _get_diff_results_as_list_of_dict(diff_results: list[git.Diff]) -> list[dict[str, str]]:
    return [
        {
            "a_path": item.a_path or "New Addition",
            "b_path": item.b_path or "Deleted",
            "diff": cast(bytes, item.diff).decode("utf-8"),
        }
        for item in diff_results
    ]


def _format_diff_results_as_json(diff_results: list[git.Diff]) -> str:
    return json.dumps(
        _get_diff_results_as_list_of_dict(diff_results),
        indent=2,
        ensure_ascii=False,
    )


def _get_commit_history(repo: git.Repo, ancestor: str) -> list[git.Commit]:
    return list(repo.iter_commits(rev=f"{ancestor}..HEAD"))


def _format_commit_history_as_plain_text(commits: list[git.Commit], ancestor: str) -> str:
    if not commits:
        return f"No commits found between {ancestor} and HEAD."

    commit_messages = ("\n\n" + "-" * 10 + "\n\n").join(
        [
            f"{commit.hexsha} by {str(commit.author)} at {commit.authored_datetime.astimezone(timezone.utc).isoformat()}\n\n{str(commit.message).strip()}"
            for commit in commits
        ]
    )
    return f"Commit messages between {ancestor} and HEAD:\n" + "-" * 10 + "\n\n" + commit_messages


def _format_commit_history_as_json_obj(commits: list[git.Commit]) -> list[dict[str, str]]:
    return [
        {
            "hexsha": commit.hexsha,
            "author": str(commit.author),
            "create_time": commit.authored_datetime.astimezone(timezone.utc).isoformat(),
            "message": str(commit.message).strip(),
        }
        for commit in commits
    ]


def _should_exclude(path: str | None, excludes: list[str]) -> bool:
    if not path:
        return False
    path_obj = PurePath(path)
    for pattern in excludes:
        if path_obj.match(pattern):
            return True
        # Workaround for root-level files when matching **/ patterns on Python versions before 3.13
        if pattern.startswith("**/") and path_obj.match(pattern[3:]):
            return True
    return False


def _get_diff_results(
    source_commit: git.Commit, target_commit: git.Commit | None, excludes: list[str]
) -> list[git.Diff]:
    if target_commit is None:
        # Note: source_commit.diff() compares source with the index (staged changes)
        #       source_commit.diff(None) compares source with the working tree
        diff_results = source_commit.diff(create_patch=True)
    else:
        diff_results = source_commit.diff(target_commit, create_patch=True)

    return [
        item
        for item in diff_results
        if not _should_exclude(item.a_path, excludes) and not _should_exclude(item.b_path, excludes)
    ]


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
        self.json_format = os.environ.get("GIT_OUTPUT_FORMAT", "json").lower() == "json"

    async def get_diff_data(self, ancestor: str) -> list[dict[str, str]]:
        if not ancestor:
            raise ValueError("Ancestor argument required")
        diff_results = _get_diff_results(self.repo.commit(ancestor), self.repo.head.commit, self.excludes)
        return _get_diff_results_as_list_of_dict(diff_results)

    async def get_cached_diff_data(self) -> list[dict[str, str]]:
        diff_results = _get_diff_results(self.repo.head.commit, None, self.excludes)
        return _get_diff_results_as_list_of_dict(diff_results)

    async def get_commit_messages_data(self, ancestor: str) -> list[dict[str, str]]:
        if not ancestor:
            raise ValueError("Ancestor argument required")
        try:
            commits = _get_commit_history(self.repo, ancestor)
            return _format_commit_history_as_json_obj(commits)
        except git.GitCommandError as e:
            raise ValueError(f"Error executing Git command: {str(e)}")

    def _get_formatted_context(
        self,
        diff_ancestor: str,
        commit_ancestor: str | None,
        diff_target: str | None = "HEAD",
    ) -> tuple[str, str, list[git.Diff], int]:
        source_commit = self.repo.commit(diff_ancestor)
        target_commit = self.repo.commit(diff_target) if diff_target else None

        diff_results = _get_diff_results(source_commit, target_commit, self.excludes)
        if commit_ancestor:
            commits = _get_commit_history(self.repo, commit_ancestor)
        else:
            commits = []

        if self.json_format:
            commit_history_obj = _format_commit_history_as_json_obj(commits)
            diff_obj = _get_diff_results_as_list_of_dict(diff_results)
            data = {
                "commit_history": commit_history_obj,
                "diff": diff_obj,
            }
            content_str = json.dumps(data, indent=2, ensure_ascii=False)
            format_str = "the JSON format"
        else:
            diff_str = _format_diff_results_as_plain_text(diff_results)
            if commit_ancestor:
                commit_history_str = _format_commit_history_as_plain_text(commits, commit_ancestor)
                content_str = commit_history_str + "\n\n" + diff_str
            else:
                content_str = diff_str
            format_str = "plain text"
        return content_str, format_str, diff_results, len(commits)

    async def generate_pr_desc_prompt(
        self, ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")]
    ) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        try:
            content_str, format_str, _, _ = self._get_formatted_context(ancestor, ancestor, "HEAD")

            prompt_text = (
                content_str
                + f"\n\nAbove is the commit history and diff results between HEAD and {ancestor} in {format_str}.\n"
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

    async def generate_commit_message_prompt(self, num_commits: int = 5) -> PromptMessage:
        try:
            if num_commits > 0:
                commit_ancestor = f"HEAD~{num_commits}"
            else:
                commit_ancestor = None

            content_str, format_str, diff_results, actual_num_commits = self._get_formatted_context(
                "HEAD", commit_ancestor, None
            )

            if len(diff_results) == 0:
                return PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text="Let the user know that there are no staged changes to generate a commit message for. If there are unstaged changes, ask if they would like to stage them. Instruct the user to rerun the command after staging the changes.",
                    ),
                )

            if actual_num_commits > 0:
                context_desc = f" and the commit message from the last {actual_num_commits} commits"
            else:
                context_desc = ""

            prompt_text = f"""
Create a commit message for the staged changes in Git. Wrap the generated message in a Markdown triple-backtick block. Example:

```markdown
This is a Git commit message.
```

Additionally, point out any potential issues in the changes at the end of the output, outside the triple-backtick block.


Here are the staged changes{context_desc} in {format_str}:

{content_str}
"""
            LOGGER.debug("Prompt generated:\n%s", prompt_text)
            return PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=prompt_text,
                ),
            )
        except Exception as e:
            raise ValueError(f"Error generating the final prompt for generate-commit-message: {str(e)}")

    async def git_diff_prompt(
        self, ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")]
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

    async def git_commit_messages_prompt(
        self,
        ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")],
    ) -> PromptMessage:
        if not ancestor:
            raise ValueError("Ancestor argument required")

        try:
            commits = _get_commit_history(self.repo, ancestor)
            if self.json_format is False:
                prompt_text = _format_commit_history_as_plain_text(commits, ancestor)
            else:
                if not commits:
                    prompt_text = json.dumps({"error_message": f"No commits found between {ancestor} and HEAD."})
                else:
                    commit_messages = _format_commit_history_as_json_obj(commits)
                    prompt_text = json.dumps(
                        commit_messages,
                        indent=2,
                        ensure_ascii=False,
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


GIT_METHOD_COLLECTION = GitMethodCollection()


@APP.prompt(
    name="generate-pr-desc",
    description="Generate PR Description based on the diff between the HEAD and the ancestor branch or commit",
)
async def generate_pr_desc_wrapper(
    ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")],
) -> PromptMessage:
    if ancestor == "$1":
        # Workaround for template-based workflow (e.g., OpenCode)
        # Always use the main branch as the ancestor
        ancestor = "main"
    LOGGER.info(
        "Generating PR descriptions based on the diff between the HEAD and the ancestor branch or commit (%s)", ancestor
    )
    return await GIT_METHOD_COLLECTION.generate_pr_desc_prompt(ancestor)


@APP.prompt(
    name="generate-commit-message",
    description="Generate commit message based on the diff between the files in the staging area (the index) and the HEAD",
)
async def generate_commit_message_wrapper(
    num_commits: Annotated[
        str,
        Field(
            "5", description="Number of recent commit messages to include in the context. Set to 0 to exclude history."
        ),
    ] = "5",
) -> PromptMessage:
    try:
        if num_commits == "$1":
            # Workaround for template-based workflow (e.g., OpenCode)
            # Always use the default number of commit number
            num_commits_int = 5
        else:
            num_commits_int = int(num_commits)
    except ValueError as e:
        LOGGER.error("Number of commits (%s) must be an integer: %s", num_commits, e)
        raise ValueError(f"Number of commits must be an integer: {e}")
    LOGGER.info(
        "Generating a commit message based on the staged changes and commit messages from %s previous commits",
        num_commits_int,
    )
    if num_commits_int < 0:
        raise ValueError("Number of commits must be zero or a positive integer")
    return await GIT_METHOD_COLLECTION.generate_commit_message_prompt(num_commits_int)


@APP.prompt(
    name="git-diff",
    description="Generate a diff between the HEAD and the ancestor branch or commit",
)
async def git_diff_wrapper(
    ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")],
) -> PromptMessage:
    LOGGER.info("Getting diff between HEAD and ancestor %s", ancestor)
    return await GIT_METHOD_COLLECTION.git_diff_prompt(ancestor)


@APP.prompt(
    name="git-cached-diff",
    description="Generate a diff between the files in the staging area (the index) and the HEAD",
)
async def git_cached_diff_wrapper() -> PromptMessage:
    LOGGER.info("Getting cached diff")
    return await GIT_METHOD_COLLECTION.git_cached_diff_prompt()


@APP.prompt(
    name="git-commit-messages",
    description="Get commit messages between the ancestor and HEAD",
)
async def git_commit_messages_wrapper(
    ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")],
) -> PromptMessage:
    LOGGER.info("Getting commit messages starting from %s to HEAD", ancestor)
    return await GIT_METHOD_COLLECTION.git_commit_messages_prompt(ancestor)


# Tools
@APP.tool(
    name="git-diff",
    description="Get a diff between the HEAD and the ancestor branch or commit",
)
async def git_diff_tool(
    ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")],
) -> list[dict[str, str]]:
    return await GIT_METHOD_COLLECTION.get_diff_data(ancestor)


@APP.tool(
    name="git-cached-diff",
    description="Get a diff between the files in the staging area (the index) and the HEAD",
)
async def git_cached_diff_tool() -> list[dict[str, str]]:
    return await GIT_METHOD_COLLECTION.get_cached_diff_data()


@APP.tool(
    name="git-commit-messages",
    description="Get commit messages between the ancestor and HEAD",
)
async def git_commit_messages_tool(
    ancestor: Annotated[str, Field(..., description="The ancestor commit hash or branch name")],
) -> list[dict[str, str]]:
    return await GIT_METHOD_COLLECTION.get_commit_messages_data(ancestor)
