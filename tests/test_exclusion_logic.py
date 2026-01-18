import unittest
from git_prompts_mcp_server.server import _should_exclude


class TestExclusionLogic(unittest.TestCase):
    """Tests for the exclusion logic using PurePath matching."""

    def test_should_exclude_basic(self):
        """Test basic filename and extension matching."""
        excludes = ["*.log"]
        self.assertTrue(_should_exclude("error.log", excludes))
        self.assertFalse(_should_exclude("main.py", excludes))

    def test_should_exclude_nested_match(self):
        """Test that a filename pattern matches nested files (suffix matching)."""
        excludes = ["target.txt"]
        path = "a/b/c/target.txt"
        # PurePath.match("target.txt") should match if the path ends with "target.txt"
        self.assertTrue(_should_exclude(path, excludes), f"Expected '{path}' to match pattern '{excludes[0]}'")

    def test_should_exclude_recursive_pattern(self):
        """Test recursive double-asterisk patterns matching at root and in subdirectories."""
        excludes = ["**/secret.txt"]
        self.assertTrue(_should_exclude("secret.txt", excludes))
        self.assertTrue(_should_exclude("subdir/secret.txt", excludes))
        self.assertTrue(_should_exclude("deep/nested/secret.txt", excludes))
        self.assertFalse(_should_exclude("not_secret.txt", excludes))

    def test_should_exclude_none_path(self):
        """Test that a None path is not excluded."""
        excludes = ["*.txt"]
        self.assertFalse(_should_exclude(None, excludes))

    def test_should_exclude_exact_match(self):
        """Test exact filename matching and suffix matching for JSON files."""
        excludes = ["config.json"]
        self.assertTrue(_should_exclude("config.json", excludes))
        self.assertTrue(_should_exclude("src/config.json", excludes))

    def test_should_exclude_multiple_patterns(self):
        """Test that exclusion works if any of the multiple patterns match."""
        excludes = ["*.tmp", "dist/*"]
        self.assertTrue(_should_exclude("file.tmp", excludes))
        self.assertTrue(_should_exclude("dist/bundle.js", excludes))
        self.assertFalse(_should_exclude("src/app.js", excludes))
