import os
import logging
from enum import Enum
from pathlib import Path
from datetime import datetime

import typer

from .version import __version__


class Format(str, Enum):
    JSON = "json"
    TEXT = "text"


def _main(repository: Path, excludes: list[str] = [], format: Format = Format.TEXT) -> None:
    os.system(f"notify-send 'Git Prompts MCP server version {__version__} is starting'")
    os.environ["GIT_REPOSITORY"] = str(repository.resolve())
    assert all(("," not in x for x in excludes)), "Excluded item cannot contain commas"
    os.environ["GIT_EXCLUDES"] = ",".join(excludes)
    os.environ["GIT_OUTPUT_FORMAT"] = format.value

    from .server import APP

    APP.run()


def entry_point():
    logging.basicConfig(
        format="[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    # Export log to a temporary file under /tmp
    tmp_log_file = Path(f"/tmp/git_prompts_mcp_{datetime.now().strftime('%Y%m%d%H%M%S')}.log")
    file_handler = logging.FileHandler(tmp_log_file)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s] %(message)s"))
    logging.getLogger().addHandler(file_handler)
    typer.run(_main)


if __name__ == "__main__":
    entry_point()
