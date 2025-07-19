"""CLI for testing the MCP methods.

Prerequiesite - These environment variables need to be set:

1. `GIT_REPOSITORY`
2. `GIT_OUTPUT_FORMAT`
3. `GIT_EXCLUDES`
"""

import asyncio

import typer
from fastmcp import Client

from .server import APP as MCP_APP

CLIENT = Client(MCP_APP)

TYPER_APP = typer.Typer()


@TYPER_APP.command()
def git_cached_diff():
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-cached-diff")
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


@TYPER_APP.command()
def git_commit_messages(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-commit-messages", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


@TYPER_APP.command()
def git_diff(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("git-diff", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


@TYPER_APP.command()
def generate_pr_desc(ancestor: str):
    async def _internal_func():
        async with CLIENT:
            result = await CLIENT.get_prompt("generate-pr-desc", {"ancestor": ancestor})
            print(result.messages[0].content.text)  # type: ignore

    asyncio.run(_internal_func())


if __name__ == "__main__":
    TYPER_APP()
