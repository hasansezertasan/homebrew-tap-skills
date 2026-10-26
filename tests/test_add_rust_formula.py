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

    def test_implicit_binaries_are_merged_without_duplicates(self) -> None:
        self.assertEqual(
            arf.binary_names({"bin": [{"name": "a"}]}, "pkg", ["a", "tool"]),
            ["a", "tool"])

    def test_src_bin_only_crate_has_no_package_named_binary(self) -> None:
        self.assertEqual(arf.binary_names({}, "pkg", ["x", "y"]), ["x", "y"])


class InheritedTest(unittest.TestCase):
    def test_direct_string(self) -> None:
        self.assertEqual(arf.inherited({"license": " MIT "}, "license", {}), "MIT")

    def test_workspace_inherited(self) -> None:
        self.assertEqual(arf.inherited(
            {"license": {"workspace": True}}, "license", {"license": "MIT"}), "MIT")

    def test_unresolvable_is_empty(self) -> None:
        self.assertEqual(arf.inherited({"license": {"workspace": True}}, "license", {}), "")

    def test_license_workspace_does_not_crash(self) -> None:
        self.assertEqual(arf.spdx_from_github(
            {}, {"package": {"license": {"workspace": True}}}, {"license": "Apache-2.0"}),
            "Apache-2.0")


class ReachableTest(unittest.TestCase):
    def test_rejects_non_http_schemes(self) -> None:
        for url in ("example.com", "file:///etc/passwd", "ftp://example.com"):
            self.assertFalse(arf.reachable(url), url)


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
        out = self.render(path="crates/cli")
        self.assertIn('*std_cargo_args(path: "crates/cli")', out)
        self.assertNotIn("*std_cargo_args, path", out)

    def test_simple_license_is_a_string(self) -> None:
        self.assertIn('  license "MIT"\n', self.render())

    def test_or_license_becomes_any_of(self) -> None:
        out = self.render(license_id="MIT OR Apache-2.0")
        self.assertIn('license any_of: ["MIT", "Apache-2.0"]', out)

    def test_and_license_becomes_all_of(self) -> None:
        out = self.render(license_id="MIT AND Zlib")
        self.assertIn('license all_of: ["MIT", "Zlib"]', out)

    def test_test_command_keeps_bin_interpolation(self) -> None:
        self.assertIn('shell_output("#{bin}/amb --version")', self.render())

    def test_untrusted_desc_is_escaped(self) -> None:
        out = self.render(desc='x" #{system "id"}')
        self.assertIn('desc "x\\" \\#{system \\"id\\"}"', out)


class ImplicitBinariesTest(unittest.TestCase):
    def test_src_bin_dir_needs_main_rs(self) -> None:
        listings = {
            "src": [],
            "src/bin": [{"name": "w.rs", "type": "file"},
                        {"name": "helpers", "type": "dir"},
                        {"name": "tool", "type": "dir"}],
            "src/bin/helpers": [{"name": "lib.rs", "type": "file"}],
            "src/bin/tool": [{"name": "main.rs", "type": "file"}],
        }

        def fake(url: str):
            return listings[url.split("/contents/")[1].split("?")[0]]

        original = arf.fetch_json
        arf.fetch_json = fake
        try:
            self.assertEqual(arf.implicit_binaries("o", "r", "v1", "", "pkg"),
                             ["w", "tool"])
        finally:
            arf.fetch_json = original


class DefaultTestCommandTest(unittest.TestCase):
    def test_uses_binary(self) -> None:
        self.assertEqual(arf.default_test_command("amb"), "#{bin}/amb --version")


if __name__ == "__main__":
    unittest.main()
