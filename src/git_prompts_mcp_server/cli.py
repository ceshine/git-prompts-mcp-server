"""CLI for testing the MCP methods.

Prerequisite - These environment variables need to be set:

1. `GIT_REPOSITORY`
2. `GIT_EXCLUDES`

Note: `GIT_OUTPUT_FORMAT` is set to `json`.
"""

import json
import asyncio
from collections.abc import Awaitable
from typing import TypeVar

import typer
from fastmcp import Client

from .server import APP as MCP_APP

CLIENT = Client(MCP_APP)
TYPER_APP = typer.Typer()
T = TypeVar("T")


def run_sync(coro: Awaitable[T]) -> T:
    """Runs an asynchronous coroutine synchronously by managing event loops.

    This function allows running awaitable coroutines in synchronous contexts. It checks if
    there's already a running event loop and raises an error if so. Otherwise, it creates a
    new event loop, runs the coroutine until completion, and closes the loop.

    Args:
        coro: An awaitable coroutine to execute.

    Returns:
        The result of the coroutine execution.

    Raises:
        RuntimeError: If called within a running event loop.
    """
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is not None and running_loop.is_running():
        raise RuntimeError("Cannot run a coroutine in a running event loop")

    running_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(running_loop)

    try:
        return running_loop.run_until_complete(coro)
    finally:
        running_loop.close()


@TYPER_APP.command()
def prompt_git_cached_diff():
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-cached-diff")
            print(result.messages[0].content.text)  # pyright: ignore[reportAttributeAccessIssue]

    _ = run_sync(_internal_func())


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

    _ = run_sync(_internal_func())


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

    _ = run_sync(_internal_func())


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

    _ = run_sync(_internal_func())


@TYPER_APP.command()
def prompt_git_commit_messages(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-commit-messages", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # pyright: ignore[reportAttributeAccessIssue]

    _ = run_sync(_internal_func())


@TYPER_APP.command()
def prompt_git_diff(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-diff", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # pyright: ignore[reportAttributeAccessIssue]

    _ = run_sync(_internal_func())


@TYPER_APP.command()
def prompt_generate_pr_desc(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("generate-pr-desc", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # pyright: ignore[reportAttributeAccessIssue]

    _ = run_sync(_internal_func())


@TYPER_APP.command()
def prompt_generate_commit_message(num_commits: int | None = None):
    async def _internal_func():
        async with CLIENT:
            if num_commits is not None:
                result = await CLIENT.get_prompt("generate-commit-message", {"num_commits": num_commits})
            else:
                result = await CLIENT.get_prompt("generate-commit-message")
            print(result.messages[0].content.text)  # pyright: ignore[reportAttributeAccessIssue]

    _ = run_sync(_internal_func())


if __name__ == "__main__":
    TYPER_APP()
