import os
import json
import logging
from fnmatch import fnmatch
from pathlib import Path
from typing import cast

import git
import mcp.types as types
from mcp.server import Server, stdio, models, NotificationOptions

PROMPTS = {
    "generate-pr-desc": types.Prompt(
        name="generate-pr-desc",
        description="Generate PR Description based on the diff between the HEAD and the ancestor branch or commit",
        arguments=[
            # Note: Zed only supports one prompt argument
            # Reference: https://github.com/zed-industries/zed/issues/21944
            types.PromptArgument(
                name="ancestor",
                description="The ancestor branch or commit",
                required=True,
            ),
        ],
    ),
    "git-diff": types.Prompt(
        name="git-diff",
        description="Generate a diff between the HEAD and the ancestor branch or commit",
        arguments=[
            # Note: Zed only supports one prompt argument
            # Reference: https://github.com/zed-industries/zed/issues/21944
            types.PromptArgument(
                name="ancestor",
                description="The ancestor branch or commit",
                required=True,
            ),
        ],
    ),
}


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
    repo: git.Repo, source_commit: git.Commit, target_commit: git.Commit, excludes: list[str]
) -> list[git.Diff]:
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
        os.system("notify-send 'Git Prompt MCP server failed to start'")
        return

    # Initialize server
    app = Server("document-conversion-server")

    @app.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        return list(PROMPTS.values())

    @app.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> types.GetPromptResult:
        if name not in PROMPTS:
            raise ValueError(f"Prompt not found: {name}")

        if name == "generate-pr-desc":
            if not arguments:
                raise ValueError("Arguments required")

            diff_results = _get_diff_results(
                repo, repo.commit(arguments.get("ancestor")), repo.commit(arguments.get("HEAD")), excludes
            )

            try:
                if json_format is True:
                    diff_str = _format_diff_results_as_json(diff_results)
                else:
                    diff_str = _format_diff_results_as_plain_text(diff_results)

                prompt = (
                    diff_str
                    + f"\n\n Above is the diff results for a pull request in {'the JSON format' if json_format else 'plain text'}. Please create descriptions for this pull request."
                )
                return types.GetPromptResult(
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text",
                                text=prompt,
                            ),
                        )
                    ]
                )
            except Exception as e:
                raise ValueError(f"Error generating the final prompt: {str(e)}")
        elif name == "git-diff":
            try:
                if not arguments:
                    raise ValueError("Arguments required")

                diff_results = _get_diff_results(
                    repo, repo.commit(arguments.get("ancestor")), repo.commit(arguments.get("HEAD")), excludes
                )

                if json_format is True:
                    diff_str = _format_diff_results_as_json(diff_results)
                else:
                    diff_str = _format_diff_results_as_plain_text(diff_results)

                prompt = (
                    diff_str
                    + f"\n\n Above is the diff results for a pull request in {'the JSON format' if json_format else 'plain text'}."
                )
                return types.GetPromptResult(
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text",
                                text=prompt,
                            ),
                        )
                    ]
                )
            except Exception as e:
                raise ValueError(f"Error generating the final prompt: {str(e)}")
        raise ValueError("Prompt implementation not found")

    async with stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            models.InitializationOptions(
                server_name="git_prompt_mcp_server",
                server_version="0.0.1",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
