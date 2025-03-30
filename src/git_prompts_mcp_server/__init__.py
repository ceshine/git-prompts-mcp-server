import os
import asyncio
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime

import typer

from .server import run


class Format(str, Enum):
    JSON = "json"
    TEXT = "text"


def _main(repository: Path, excludes: list[str] = [], format: Format = Format.TEXT) -> None:
    os.system("notify-send 'Git Prompt MCP server is starting'")
    asyncio.run(run(repository, excludes, json_format=format == Format.JSON))


def entry_point():
    logging.basicConfig(
        format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    # Export log to a temporary file under /tmp
    tmp_log_file = Path(f"/tmp/git_prompt_mcp_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
    file_handler = logging.FileHandler(tmp_log_file)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)
    typer.run(_main)


if __name__ == "__main__":
    entry_point()
