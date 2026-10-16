"""Tests for repository-to-tap name resolution."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/homebrew-add/scripts"))

import tap_name  # noqa: E402


class FromRemoteTest(unittest.TestCase):
    def test_https_homebrew_prefix(self) -> None:
        self.assertEqual(
            tap_name.from_remote("https://github.com/acme/homebrew-tools.git"),
            "acme/tools",
        )

    def test_ssh_homebrew_prefix(self) -> None:
        self.assertEqual(
            tap_name.from_remote("git@github.com:acme/homebrew-tools.git"),
            "acme/tools",
        )

    def test_scp_style_without_user(self) -> None:
        self.assertEqual(
            tap_name.from_remote("github.com:acme/homebrew-tools.git"),
            "acme/tools",
        )

    def test_repository_without_prefix(self) -> None:
        self.assertEqual(
            tap_name.from_remote("https://github.com/acme/tools.git"),
            "acme/tools",
        )

    def test_non_github_remote(self) -> None:
        self.assertIsNone(tap_name.from_remote("https://example.com/acme/tools.git"))

    def test_lookalike_host(self) -> None:
        self.assertIsNone(tap_name.from_remote("https://notgithub.com/acme/tools.git"))

    def test_trailing_slash(self) -> None:
        self.assertEqual(
            tap_name.from_remote("https://github.com/acme/homebrew-tools/"),
            "acme/tools",
        )


class TapRootTest(unittest.TestCase):
    def test_argument_wins_over_environment(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            (Path(a) / "Formula").mkdir()
            (Path(b) / "Casks").mkdir()
            with mock.patch.dict(os.environ, {"HOMEBREW_TAP_DIR": b}):
                self.assertEqual(tap_name.tap_root(a), Path(a).resolve())

    def test_environment_then_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as env, tempfile.TemporaryDirectory() as cwd:
            (Path(env) / "Casks").mkdir()
            (Path(cwd) / "Formula").mkdir()
            with mock.patch.dict(os.environ, {"HOMEBREW_TAP_DIR": env}):
                self.assertEqual(tap_name.tap_root(None), Path(env).resolve())
            environ = {k: v for k, v in os.environ.items() if k != "HOMEBREW_TAP_DIR"}
            with mock.patch.dict(os.environ, environ, clear=True), \
                    mock.patch.object(Path, "cwd", return_value=Path(cwd)):
                self.assertEqual(tap_name.tap_root(None), Path(cwd).resolve())

    def test_rejects_a_directory_that_is_not_a_tap(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(SystemExit) as raised:
                tap_name.tap_root(empty)
            self.assertIn("--tap-dir", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
