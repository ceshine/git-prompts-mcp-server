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
        self.test_dir = "test_repo"
        os.makedirs(self.test_dir, exist_ok=True)
        repo = git.Repo.init(self.test_dir, initial_branch="main")
        with open(os.path.join(self.test_dir, "file.txt"), "w") as f:
            f.write("initial content")
        repo.index.add(["file.txt"])
        repo.index.commit("initial commit")
        os.environ["GIT_REPOSITORY"] = self.test_dir
        os.environ["GIT_EXCLUDES"] = ""
        os.environ["GIT_OUTPUT_FORMAT"] = "text"
        self.git_methods = GitMethodCollection()

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

    @patch("git_prompts_mcp_server.server._get_diff_results")
    def test_generate_pr_desc_prompt(self, mock_get_diff_results):
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
        prompt = asyncio.run(self.git_methods.generate_pr_desc_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("File: file1.txt -> file1.txt", prompt.content.text)
        self.assertIn("File: New Addition -> file2.txt", prompt.content.text)
        self.assertIn("plain text", prompt.content.text)

        # Test JSON format
        os.environ["GIT_OUTPUT_FORMAT"] = "json"
        self.git_methods = GitMethodCollection()
        prompt = asyncio.run(self.git_methods.generate_pr_desc_prompt("main"))
        assert isinstance(prompt.content, TextContent)
        self.assertIn("the JSON format", prompt.content.text)
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
