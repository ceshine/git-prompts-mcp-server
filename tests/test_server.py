import os
import json
import shutil
import asyncio
import unittest
from unittest.mock import patch, MagicMock

import git
from mcp.types import TextContent

from git_prompts_mcp_server.server import (
    GitMethodCollection,
    _format_diff_results_as_plain_text,
    _format_diff_results_as_json,
)


class TestGitMethodCollection(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_repo"  # pyright: ignore[reportUninitializedInstanceVariable]
        os.makedirs(self.test_dir, exist_ok=True)
        repo = git.Repo.init(self.test_dir, initial_branch="main")
        with open(os.path.join(self.test_dir, "file.txt"), "w") as f:
            f.write("initial content")
        repo.index.add(["file.txt"])
        repo.index.commit("initial commit")
        os.environ["GIT_REPOSITORY"] = self.test_dir
        os.environ["GIT_EXCLUDES"] = ""
        os.environ["GIT_OUTPUT_FORMAT"] = "text"
        self.git_methods = GitMethodCollection()  # pyright: ignore[reportUninitializedInstanceVariable]

    def tearDown(self):
        del os.environ["GIT_REPOSITORY"]
        del os.environ["GIT_EXCLUDES"]
        del os.environ["GIT_OUTPUT_FORMAT"]
        shutil.rmtree(self.test_dir)

    def test_format_diff_results_as_plain_text(self):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = "file1.txt"
        diff1.b_path = "file1.txt"
        diff1.diff = b"--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-initial content\n+modified content"

        diff2 = MagicMock(spec=git.Diff)
        diff2.a_path = None
        diff2.b_path = "file2.txt"
        diff2.diff = b"--- /dev/null\n+++ b/file2.txt\n@@ -0,0 +1 @@\n+new file content"

        formatted_text = _format_diff_results_as_plain_text([diff1, diff2])
        self.assertIn("File: file1.txt -> file1.txt", formatted_text)
        self.assertIn("--- a/file1.txt", formatted_text)
        self.assertIn("File: New Addition -> file2.txt", formatted_text)
        self.assertIn("--- /dev/null", formatted_text)

    def test_format_diff_results_as_json(self):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = "file1.txt"
        diff1.b_path = "file1.txt"
        diff1.diff = b"--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-initial content\n+modified content"

        diff2 = MagicMock(spec=git.Diff)
        diff2.a_path = None
        diff2.b_path = "file2.txt"
        diff2.diff = b"--- /dev/null\n+++ b/file2.txt\n@@ -0,0 +1 @@\n+new file content"

        formatted_json = _format_diff_results_as_json([diff1, diff2])
        data = json.loads(formatted_json)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["a_path"], "file1.txt")
        self.assertIn("--- a/file1.txt", data[0]["diff"])
        self.assertEqual(data[1]["a_path"], "New Addition")
        self.assertIn("--- /dev/null", data[1]["diff"])

    @patch("git_prompts_mcp_server.server._get_commit_history")
    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_generate_pr_desc_prompt(self, mock_get_diff_results, mock_get_commit_history):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = "file1.txt"
        diff1.b_path = "file1.txt"
        diff1.diff = b"--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-initial content\n+modified content"

        diff2 = MagicMock(spec=git.Diff)
        diff2.a_path = None
        diff2.b_path = "file2.txt"
        diff2.diff = b"--- /dev/null\n+++ b/file2.txt\n@@ -0,0 +1 @@\n+new file content"
        mock_get_diff_results.return_value = [diff1, diff2]

        mock_commit = MagicMock()
        mock_commit.hexsha = "abcdef"
        mock_commit.author.name = "Test Author"
        mock_commit.authored_datetime.astimezone().isoformat.return_value = "2023-01-01T12:00:00+00:00"
        mock_commit.message = "feat: a new feature"
        mock_get_commit_history.return_value = [mock_commit]

        # Test plain text format
        prompt = asyncio.run(self.git_methods.generate_pr_desc_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("File: file1.txt -> file1.txt", prompt.content.text)
        self.assertIn("File: New Addition -> file2.txt", prompt.content.text)
        self.assertIn("feat: a new feature", prompt.content.text)
        self.assertIn("plain text", prompt.content.text)

        # Test JSON format
        os.environ["GIT_OUTPUT_FORMAT"] = "json"
        self.git_methods = GitMethodCollection()
        prompt = asyncio.run(self.git_methods.generate_pr_desc_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("the JSON format", prompt.content.text)
        # check the content
        content_json = json.loads(prompt.content.text.split("\n\n")[0])
        self.assertIn("commit_history", content_json)
        self.assertIn("diff", content_json)
        self.assertEqual(len(content_json["commit_history"]), 1)
        self.assertEqual(content_json["commit_history"][0]["message"], "feat: a new feature")
        self.assertEqual(len(content_json["diff"]), 2)
        # Reset to default
        os.environ["GIT_OUTPUT_FORMAT"] = "text"

    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_git_cached_diff_prompt(self, mock_get_diff_results):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = None
        diff1.b_path = "file3.txt"
        diff1.diff = b"--- /dev/null\n+++ b/file3.txt\n@@ -0,0 +1 @@\n+staged content"
        mock_get_diff_results.return_value = [diff1]

        # Test plain text format
        prompt = asyncio.run(self.git_methods.git_cached_diff_prompt())
        assert isinstance(prompt.content, TextContent)
        self.assertIn("File: New Addition -> file3.txt", prompt.content.text)
        self.assertIn("plain text", prompt.content.text)

        # Test JSON format
        os.environ["GIT_OUTPUT_FORMAT"] = "json"
        self.git_methods = GitMethodCollection()
        prompt = asyncio.run(self.git_methods.git_cached_diff_prompt())
        assert isinstance(prompt.content, TextContent)
        self.assertIn("the JSON format", prompt.content.text)
        # Reset to default
        os.environ["GIT_OUTPUT_FORMAT"] = "text"

    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_get_diff_data(self, mock_get_diff_results):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = "file1.txt"
        diff1.b_path = "file1.txt"
        diff1.diff = b"diff content"
        mock_get_diff_results.return_value = [diff1]

        data = asyncio.run(self.git_methods.get_diff_data("main"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["a_path"], "file1.txt")
        self.assertEqual(data[0]["diff"], "diff content")

    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_get_cached_diff_data(self, mock_get_diff_results):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = None
        diff1.b_path = "file2.txt"
        diff1.diff = b"cached diff content"
        mock_get_diff_results.return_value = [diff1]

        data = asyncio.run(self.git_methods.get_cached_diff_data())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["a_path"], "New Addition")
        self.assertEqual(data[0]["b_path"], "file2.txt")
        self.assertEqual(data[0]["diff"], "cached diff content")

    @patch("git_prompts_mcp_server.server.git.Repo")
    def test_get_commit_messages_data(self, mock_repo):
        mock_commit = MagicMock()
        mock_commit.hexsha = "12345"
        mock_commit.author.name = "Test Author"
        mock_commit.authored_datetime.astimezone().isoformat.return_value = "2023-01-01T12:00:00+00:00"
        mock_commit.message = "a commit message"
        self.git_methods.repo.iter_commits = MagicMock(return_value=[mock_commit])

        data = asyncio.run(self.git_methods.get_commit_messages_data("main"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["hexsha"], "12345")
        self.assertEqual(data[0]["message"], "a commit message")

    @patch("git_prompts_mcp_server.server.git.Repo")
    def test_git_commit_messages_prompt(self, mock_repo):
        mock_commit1 = MagicMock()
        mock_commit1.hexsha = "12345"
        mock_commit1.author.name = "Test Author"
        mock_commit1.authored_datetime.astimezone().isoformat.return_value = "2023-01-01T12:00:00+00:00"
        mock_commit1.message = "second commit"

        mock_commit2 = MagicMock()
        mock_commit2.hexsha = "67890"
        mock_commit2.author.name = "Test Author"
        mock_commit2.authored_datetime.astimezone().isoformat.return_value = "2023-01-01T11:00:00+00:00"
        mock_commit2.message = "initial commit"

        self.git_methods.repo.iter_commits = MagicMock(return_value=[mock_commit1, mock_commit2])

        # Test plain text format
        prompt = asyncio.run(self.git_methods.git_commit_messages_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("second commit", prompt.content.text)
        self.assertIn("initial commit", prompt.content.text)

        # Test JSON format
        os.environ["GIT_OUTPUT_FORMAT"] = "json"
        self.git_methods = GitMethodCollection()
        self.git_methods.repo.iter_commits = MagicMock(return_value=[mock_commit1, mock_commit2])
        prompt = asyncio.run(self.git_methods.git_commit_messages_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        data = json.loads(prompt.content.text)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["message"], "second commit")
        self.assertEqual(data[1]["message"], "initial commit")
        # Reset to default
        os.environ["GIT_OUTPUT_FORMAT"] = "text"

    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_git_diff_prompt(self, mock_get_diff_results):
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = "file1.txt"
        diff1.b_path = "file1.txt"
        diff1.diff = b"--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-initial content\n+modified content"

        diff2 = MagicMock(spec=git.Diff)
        diff2.a_path = None
        diff2.b_path = "file2.txt"
        diff2.diff = b"--- /dev/null\n+++ b/file2.txt\n@@ -0,0 +1 @@\n+new file content"
        mock_get_diff_results.return_value = [diff1, diff2]

        # Test plain text format
        prompt = asyncio.run(self.git_methods.git_diff_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("File: file1.txt -> file1.txt", prompt.content.text)
        self.assertIn("File: New Addition -> file2.txt", prompt.content.text)
        self.assertIn("plain text", prompt.content.text)

        # Test JSON format
        os.environ["GIT_OUTPUT_FORMAT"] = "json"
        self.git_methods = GitMethodCollection()
        prompt = asyncio.run(self.git_methods.git_diff_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("the JSON format", prompt.content.text)
        # Reset to default
        os.environ["GIT_OUTPUT_FORMAT"] = "text"

    @patch("git_prompts_mcp_server.server._get_commit_history")
    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_generate_commit_message_prompt(self, mock_get_diff_results, mock_get_commit_history):
        # Case 1: No staged changes
        mock_get_diff_results.return_value = []
        prompt = asyncio.run(self.git_methods.generate_commit_message_prompt())
        assert isinstance(prompt.content, TextContent)
        self.assertIn("no staged changes", prompt.content.text)

        # Setup for other cases
        diff1 = MagicMock(spec=git.Diff)
        diff1.a_path = None
        diff1.b_path = "file1.txt"
        diff1.diff = b"--- /dev/null\n+++ b/file1.txt\n@@ -0,0 +1 @@\n+staged content"
        mock_get_diff_results.return_value = [diff1]

        mock_commit = MagicMock()
        mock_commit.hexsha = "12345"
        mock_commit.author.name = "Test Author"
        mock_commit.authored_datetime.astimezone().isoformat.return_value = "2023-01-01T12:00:00+00:00"
        mock_commit.message = "recent commit"
        mock_get_commit_history.return_value = [mock_commit]

        # Case 2: Staged changes, text format, default history (5)
        prompt = asyncio.run(self.git_methods.generate_commit_message_prompt())
        assert isinstance(prompt.content, TextContent)
        self.assertIn("Create a commit message", prompt.content.text)
        self.assertIn("plain text", prompt.content.text)
        self.assertIn("File: New Addition -> file1.txt", prompt.content.text)
        self.assertIn("recent commit", prompt.content.text)
        self.assertIn("last 1 commits", prompt.content.text)

        # Case 3: Staged changes, JSON format
        os.environ["GIT_OUTPUT_FORMAT"] = "json"
        self.git_methods = GitMethodCollection()
        prompt = asyncio.run(self.git_methods.generate_commit_message_prompt())
        assert isinstance(prompt.content, TextContent)
        self.assertIn("the JSON format", prompt.content.text)

        # Verify JSON content keys presence
        self.assertIn('"diff": [', prompt.content.text)
        self.assertIn('"commit_history": [', prompt.content.text)
        self.assertIn("recent commit", prompt.content.text)

        # Reset to default
        os.environ["GIT_OUTPUT_FORMAT"] = "text"
        self.git_methods = GitMethodCollection()

        # Case 4: No history (num_commits=0)
        mock_get_commit_history.reset_mock()
        prompt = asyncio.run(self.git_methods.generate_commit_message_prompt(num_commits=0))
        self.assertIn("Create a commit message", prompt.content.text)
        self.assertNotIn("recent commit", prompt.content.text)
        self.assertNotIn("last 5 commits", prompt.content.text)
        mock_get_commit_history.assert_not_called()

        # Case 5: Custom history (num_commits=3)
        prompt = asyncio.run(self.git_methods.generate_commit_message_prompt(num_commits=3))
        self.assertIn("last 1 commits", prompt.content.text)
        mock_get_commit_history.assert_called()
