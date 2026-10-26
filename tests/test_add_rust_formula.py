"""Tests for ``add_rust_formula.py`` (stdlib ``unittest``, no network).

Only the pure helpers are exercised; the GitHub calls and the archive download
are left to a real scaffold run. Run with ``python -m unittest discover -s tests``.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/homebrew-add/scripts"))

import add_rust_formula as arf  # noqa: E402


class BinaryNamesTest(unittest.TestCase):
    def test_explicit_bin_tables_win(self) -> None:
        manifest = {"bin": [{"name": "a"}, {"name": "b"}]}
        self.assertEqual(arf.binary_names(manifest, "pkg"), ["a", "b"])

    def test_defaults_to_package_name(self) -> None:
        self.assertEqual(arf.binary_names({}, "pkg"), ["pkg"])


class LicenseTest(unittest.TestCase):
    def test_manifest_wins(self) -> None:
        self.assertEqual(arf.spdx_from_github(
            {"license": {"spdx_id": "Apache-2.0"}}, {"package": {"license": "MIT"}}), "MIT")

    def test_falls_back_to_github(self) -> None:
        self.assertEqual(arf.spdx_from_github(
            {"license": {"spdx_id": "Apache-2.0"}}, {"package": {}}), "Apache-2.0")

    def test_noassertion_is_a_todo(self) -> None:
        self.assertEqual(arf.spdx_from_github(
            {"license": {"spdx_id": "NOASSERTION"}}, {"package": {}}),
            "TODO-set-SPDX-license")

    def test_no_license_is_a_todo(self) -> None:
        self.assertEqual(arf.spdx_from_github({}, {}), "TODO-set-SPDX-license")


class RenderTest(unittest.TestCase):
    def render(self, **kw) -> str:
        args = dict(name="amb", url="https://example.test/v1.tar.gz", sha="0" * 64,
                    desc="Mixer", homepage="https://example.test", license_id="MIT",
                    test_command="#{bin}/amb --version")
        args.update(kw)
        return arf.render(**args)

    def test_builds_with_cargo(self) -> None:
        out = self.render()
        self.assertIn('depends_on "rust" => :build', out)
        self.assertIn('system "cargo", "install", *std_cargo_args\n', out)
        self.assertIn("strategy :github_latest", out)
        self.assertIn("class Amb < Formula", out)

    def test_path_for_workspace_member(self) -> None:
        self.assertIn('*std_cargo_args, path: "crates/cli"',
                      self.render(path="crates/cli"))

    def test_test_command_keeps_bin_interpolation(self) -> None:
        self.assertIn('shell_output("#{bin}/amb --version")', self.render())

    def test_untrusted_desc_is_escaped(self) -> None:
        out = self.render(desc='x" #{system "id"}')
        self.assertIn('desc "x\\" \\#{system \\"id\\"}"', out)


class DefaultTestCommandTest(unittest.TestCase):
    def test_uses_binary(self) -> None:
        self.assertEqual(arf.default_test_command("amb"), "#{bin}/amb --version")


if __name__ == "__main__":
    unittest.main()
