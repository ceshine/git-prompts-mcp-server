"""CLI for testing the MCP methods.

Prerequisite - These environment variables need to be set:

1. `GIT_REPOSITORY`
2. `GIT_EXCLUDES`

Note: `GIT_OUTPUT_FORMAT` is set to `json`.
"""

import json
import asyncio

import typer
from fastmcp import Client

from .server import APP as MCP_APP

CLIENT = Client(MCP_APP)

TYPER_APP = typer.Typer()


@TYPER_APP.command()
def prompt_git_cached_diff():
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-cached-diff")
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


@TYPER_APP.command()
def tool_git_diff(ancestor: str):
    """Run the git-diff tool."""

    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.call_tool("git-diff", {"ancestor": ancestor})
            if result.structured_content is not None:
                print(json.dumps(result.structured_content["result"], indent=2))
            else:
                print("Got an empty response")
                raise typer.Exit(1)

    asyncio.run(_internal_func())


@TYPER_APP.command()
def tool_git_cached_diff():
    """Run the git-cached-diff tool."""

    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.call_tool("git-cached-diff")
            if result.structured_content is not None:
                print(json.dumps(result.structured_content["result"], indent=2))
            else:
                print("Got an empty response")
                raise typer.Exit(1)

    asyncio.run(_internal_func())


@TYPER_APP.command()
def tool_git_commit_messages(ancestor: str):
    """Run the git-commit-messages tool."""

    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.call_tool("git-commit-messages", {"ancestor": ancestor})
            if result.structured_content is not None:
                print(json.dumps(result.structured_content["result"], indent=2))
            else:
                print("Got an empty response")
                raise typer.Exit(1)

    asyncio.run(_internal_func())


@TYPER_APP.command()
def prompt_git_commit_messages(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-commit-messages", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


@TYPER_APP.command()
def prompt_git_diff(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-diff", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


@TYPER_APP.command()
def prompt_generate_pr_desc(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("generate-pr-desc", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


if __name__ == "__main__":
    TYPER_APP()
