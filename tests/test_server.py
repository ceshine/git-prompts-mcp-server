import os
import json
from datetime import datetime, timezone
from unittest import mock

import pytest
import git
from typer.testing import CliRunner

# Assuming your server and CLI are structured in a way that allows these imports
from git_prompts_mcp_server.server import GitMethodCollection
from git_prompts_mcp_server.cli import TYPER_APP as CLI_APP


# Mock environment variables before GitMethodCollection is instantiated
@pytest.fixture(autouse=True)
def mock_env_vars():
    with mock.patch.dict(os.environ, {"GIT_REPOSITORY": "/mock/repo", "GIT_EXCLUDES": "", "GIT_OUTPUT_FORMAT": "text"}):
        yield


@pytest.fixture
def mock_env_vars_json():
    with mock.patch.dict(os.environ, {"GIT_REPOSITORY": "/mock/repo", "GIT_EXCLUDES": "", "GIT_OUTPUT_FORMAT": "json"}):
        yield


@pytest.fixture
def runner():
    return CliRunner()


# Mock for git.Commit
class MockCommit:
    def __init__(self, message, hexsha="abcdef1234567890"):
        self.message = message
        self.hexsha = hexsha
        self.author = mock.Mock()
        self.author.name = "Test Author"
        self.author.__str__ = lambda *args, **kwargs: "Test Author"
        self.authored_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def diff(self, *args, **kwargs):
        # Return a mock diff object that matches what git.Diff would return
        diff_mock = mock.Mock()
        diff_mock.a_path = "test_path"
        diff_mock.b_path = "test_path"
        diff_mock.diff = b"test diff content"
        return [diff_mock]


# Mock for git.Repo
class MockRepo:
    def __init__(self, path):
        self.path = path
        self.head = mock.Mock()
        self.head.commit = MockCommit("Initial commit")

    def commit(self, rev):
        if rev == "valid_ancestor" or rev == "HEAD" or rev == self.head.commit.hexsha:
            return MockCommit(f"Commit for {rev}")
        elif rev == "non_existent_ancestor":
            raise git.GitCommandError("commit", f"Unknown revision or path not in the working tree: '{rev}'")
        raise git.NoSuchPathError(f"Path '{rev}' does not exist in the repository")

    def iter_commits(self, rev):
        # Handle all revision formats
        if isinstance(rev, str) and ".." in rev:
            ancestor = rev.split("..")[0]
            if ancestor == "valid_ancestor":
                return [
                    MockCommit("Test commit 1", "abc123"),
                    MockCommit("Test commit 2\nThis is a multiline message.", "def456"),
                ]
            elif ancestor == "non_existent_ancestor":
                raise git.GitCommandError("log", "Invalid revision range")
            elif ancestor == "no_commits_ancestor":
                return []
        return []

    def __getattr__(self, name):
        # Handle git command execution for CLI tests
        if name == "git":
            git_mock = mock.Mock()
            git_mock.rev_list.side_effect = lambda *args, **kwargs: self._mock_git_rev_list(*args, **kwargs)
            return git_mock
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _mock_git_rev_list(self, *args, **kwargs):
        # Mock the git rev-list command behavior for CLI tests
        if "valid_ancestor..HEAD" in args[0]:
            return ["abc123", "def456"]
        elif "no_commits_ancestor..HEAD" in args[0]:
            return []
        elif "non_existent_ancestor..HEAD" in args[0]:
            raise git.GitCommandError(
                ["git", "rev-list", "non_existent_ancestor..HEAD", "--"],
                128,
                "fatal: bad revision 'non_existent_ancestor..HEAD'",
            )
        else:
            raise git.GitCommandError(
                ["git", "rev-list", "invalid_revision..HEAD", "--"], 128, "fatal: invalid revision range"
            )

    def rev_parse(self, rev):
        if rev == "HEAD":
            return "abcdef1234567890"
        raise git.GitCommandError("rev-parse", f"fatal: ambiguous argument '{rev}'")


@pytest.fixture
def mock_git_repo(monkeypatch):
    mock_repo_instance = MockRepo("/mock/repo")
    monkeypatch.setattr("git.Repo", lambda path: mock_repo_instance)
    return mock_repo_instance


# Test for valid ancestor using CLI
def test_git_commit_messages_cli_valid_ancestor(runner, mock_git_repo):
    result = runner.invoke(CLI_APP, ["git-commit-messages", "valid_ancestor"])
    assert result.exit_code == 0
    # The CLI output should contain the formatted commit messages
    assert "Commit messages between valid_ancestor and HEAD:" in result.stdout
    assert "Test commit 1" in result.stdout
    assert "Test commit 2" in result.stdout
    assert "This is a multiline message." in result.stdout


# Test for no commits between ancestor and HEAD
def test_git_commit_messages_cli_no_commits(runner, mock_git_repo):
    result = runner.invoke(CLI_APP, ["git-commit-messages", "no_commits_ancestor"])
    assert result.exit_code == 0
    expected_output = "No commits found between no_commits_ancestor and HEAD."
    assert expected_output in result.stdout


# Test for invalid ancestor using CLI
def test_git_commit_messages_cli_invalid_ancestor(runner, mock_git_repo):
    result = runner.invoke(CLI_APP, ["git-commit-messages", "non_existent_ancestor"])
    assert result.exit_code == 0  # The CLI command itself doesn't exit with error, it prints the error from server
    assert "Error executing Git command" in result.stdout


# Test for missing ancestor using CLI
def test_git_commit_messages_cli_missing_ancestor(runner):
    result = runner.invoke(CLI_APP, ["git-commit-messages"])
    assert result.exit_code != 0  # Typer should indicate an error
    assert "Missing argument 'ANCESTOR'" in result.stdout  # Typer's default error message


# Test for missing ancestor directly calling the server method
@pytest.mark.asyncio
async def test_git_commit_messages_server_missing_ancestor(mock_git_repo):
    git_methods = GitMethodCollection()

    with pytest.raises(ValueError) as excinfo:
        await git_methods.git_commit_messages_prompt(ancestor=None)  # type: ignore
    assert "Ancestor argument required" in str(excinfo.value)

    # Test the pydantic validation by not passing the argument
    with pytest.raises(ValueError) as excinfo_type:
        await git_methods.git_commit_messages_prompt()  # type: ignore
    assert "Ancestor argument required" in str(excinfo_type.value)
    assert "ancestor" in str(excinfo_type.value)  # Ensure it's from pydantic validation

    # Test with empty string
    with pytest.raises(ValueError) as excinfo_empty:
        await git_methods.git_commit_messages_prompt(ancestor="")
    assert "Ancestor argument required" in str(excinfo_empty.value)


# Test for valid ancestor, directly calling the server method
@pytest.mark.asyncio
async def test_git_commit_messages_server_valid_ancestor(mock_git_repo):
    git_methods = GitMethodCollection()
    # Ensure git_methods.repo is the mocked one
    assert isinstance(git_methods.repo, MockRepo)

    prompt_message = await git_methods.git_commit_messages_prompt(ancestor="valid_ancestor")

    # Check the structure of the response
    from mcp.types import TextContent

    assert prompt_message.role == "user"
    assert isinstance(prompt_message.content, TextContent)

    # Check that the content contains the expected formatted output
    content_text = prompt_message.content.text
    assert "Commit messages between valid_ancestor and HEAD:" in content_text
    assert "abc123 by Test Author at 2023-01-01T12:00:00+00:00" in content_text
    assert "Test commit 1" in content_text
    assert "def456 by Test Author at 2023-01-01T12:00:00+00:00" in content_text
    assert "Test commit 2\nThis is a multiline message." in content_text


# Test for invalid ancestor, directly calling the server method
@pytest.mark.asyncio
async def test_git_commit_messages_server_invalid_ancestor(mock_git_repo):
    git_methods = GitMethodCollection()
    assert isinstance(git_methods.repo, MockRepo)

    with pytest.raises(ValueError) as excinfo:
        await git_methods.git_commit_messages_prompt(ancestor="non_existent_ancestor")
    assert "Error executing Git command" in str(excinfo.value)


# Test for no commits, directly calling the server method
@pytest.mark.asyncio
async def test_git_commit_messages_server_no_commits(mock_git_repo):
    git_methods = GitMethodCollection()
    assert isinstance(git_methods.repo, MockRepo)

    from mcp.types import TextContent

    prompt_message = await git_methods.git_commit_messages_prompt(ancestor="no_commits_ancestor")
    expected_output = "No commits found between no_commits_ancestor and HEAD."
    assert isinstance(prompt_message.content, TextContent)
    assert prompt_message.content.text == expected_output


# Test JSON output format
@pytest.mark.asyncio
async def test_git_commit_messages_server_json_format_valid_ancestor(mock_env_vars_json, mock_git_repo):
    git_methods = GitMethodCollection()

    prompt_message = await git_methods.git_commit_messages_prompt(ancestor="valid_ancestor")

    from mcp.types import TextContent

    assert isinstance(prompt_message.content, TextContent)
    # Parse the JSON content
    content = json.loads(prompt_message.content.text)
    assert isinstance(content, list)
    assert len(content) == 2

    # Check first commit
    assert content[0]["hexsha"] == "abc123"
    assert content[0]["author"] == "Test Author"
    assert content[0]["create_time"] == "2023-01-01T12:00:00+00:00"
    assert content[0]["message"] == "Test commit 1"

    # Check second commit
    assert content[1]["hexsha"] == "def456"
    assert content[1]["author"] == "Test Author"
    assert content[1]["create_time"] == "2023-01-01T12:00:00+00:00"
    assert content[1]["message"] == "Test commit 2\nThis is a multiline message."


# Test JSON output format with no commits
@pytest.mark.asyncio
async def test_git_commit_messages_server_json_format_no_commits(mock_env_vars_json, mock_git_repo):
    git_methods = GitMethodCollection()

    from mcp.types import TextContent

    prompt_message = await git_methods.git_commit_messages_prompt(ancestor="no_commits_ancestor")
    assert isinstance(prompt_message.content, TextContent)

    # Parse the JSON content
    content = json.loads(prompt_message.content.text)
    assert "error_message" in content
    assert "No commits found between no_commits_ancestor and HEAD." in content["error_message"]


# Test that other methods exist and can be called (basic smoke tests)
@pytest.mark.asyncio
async def test_other_methods_exist(mock_git_repo):
    git_methods = GitMethodCollection()

    # Test that other methods exist
    assert hasattr(git_methods, "generate_pr_desc_prompt")
    assert hasattr(git_methods, "git_diff_prompt")
    assert hasattr(git_methods, "git_cached_diff_prompt")

    # Basic smoke test for git_cached_diff_prompt (doesn't need ancestor)
    prompt_message = await git_methods.git_cached_diff_prompt()
    assert prompt_message.role == "user"
    assert hasattr(prompt_message.content, "text")
