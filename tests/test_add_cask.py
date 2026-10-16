"""Tests for ``scripts/add_cask.py`` (stdlib ``unittest``, no network).

Only the pure helpers are exercised — the GitHub API calls and the asset
download (sha256) are left to a real scaffold run. Run with
``python -m unittest discover -s tests`` from the repo root.
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/homebrew-add/scripts"))

import add_cask as ac  # noqa: E402


class NameTest(unittest.TestCase):
    def test_normalize(self) -> None:
        self.assertEqual(ac.normalize("My_App.Name"), "my-app-name")


class ParseRepoTest(unittest.TestCase):
    def test_owner_repo(self) -> None:
        self.assertEqual(ac.parse_repo("o/r"), ("o", "r"))

    def test_github_url(self) -> None:
        self.assertEqual(ac.parse_repo("https://github.com/o/r"), ("o", "r"))

    def test_strips_git_suffix(self) -> None:
        self.assertEqual(ac.parse_repo("https://github.com/o/r.git"), ("o", "r"))

    def test_garbage_exits(self) -> None:
        with self.assertRaises(SystemExit):
            ac.parse_repo("not-a-repo")


class DescTest(unittest.TestCase):
    def test_capitalizes_and_strips(self) -> None:
        # A lowercase leading article is stripped like an uppercase one, and the
        # remaining first letter is capitalized for `brew audit --strict`.
        self.assertEqual(ac.clean_desc("a neat app."), "Neat app")
        self.assertEqual(ac.clean_desc("An app."), "App")
        self.assertEqual(ac.clean_desc("the widget"), "Widget")

    def test_empty(self) -> None:
        self.assertEqual(ac.clean_desc(""), "")


class SelectAssetTest(unittest.TestCase):
    def test_lone_dmg(self) -> None:
        dmg = {"name": "App.dmg"}
        self.assertIs(ac.select_asset([dmg, {"name": "notes.txt"}], None), dmg)

    def test_explicit_artifact(self) -> None:
        a, b = {"name": "App-arm64.dmg"}, {"name": "App-x64.dmg"}
        self.assertIs(ac.select_asset([a, b], "App-x64.dmg"), b)

    def test_preference_dmg_before_zip(self) -> None:
        dmg, zipp = {"name": "App.dmg"}, {"name": "App.zip"}
        self.assertIs(ac.select_asset([zipp, dmg], None), dmg)

    def test_multiple_same_suffix_exits(self) -> None:
        with self.assertRaises(SystemExit):
            ac.select_asset([{"name": "a.dmg"}, {"name": "b.dmg"}], None)

    def test_no_assets_exits(self) -> None:
        with self.assertRaises(SystemExit):
            ac.select_asset([], None)


class TemplatizeTest(unittest.TestCase):
    def test_replaces_version(self) -> None:
        self.assertEqual(ac.templatize("App-1.2.3.dmg", "1.2.3"), "App-#{version}.dmg")

    def test_warns_when_absent(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertEqual(ac.templatize("static.dmg", "1.2.3"), "static.dmg")
        self.assertIn("won't auto-update", buf.getvalue())


class RbStrTest(unittest.TestCase):
    def test_escapes_backslash_and_quote(self) -> None:
        self.assertEqual(ac._rb_str('a"b\\c'), 'a\\"b\\\\c')


class StanzaTest(unittest.TestCase):
    def test_pkg_stanza_carries_its_uninstall(self) -> None:
        # Was asserted to emit a bare `pkg` stanza with no hint, which
        # `brew audit --cask --strict` rejects. See PkgStanzaTest below.
        stanza, hint = ac.stanza_for("x.pkg", "x.pkg", "tok", "com.example.x")
        self.assertEqual(
            stanza,
            '  pkg "x.pkg"\n\n  uninstall pkgutil: "com.example.x"',
        )
        self.assertTrue(hint)

    def test_dmg_stanza_guesses_app_with_hint(self) -> None:
        line, hint = ac.stanza_for("x.dmg", "x.dmg", "tok")
        self.assertEqual(line, '  app "tok.app"')
        self.assertTrue(hint)



class VersionFromTagTest(unittest.TestCase):
    def test_strips_a_v_prefix(self) -> None:
        self.assertEqual(ac.version_from_tag("v1.2.3"), "1.2.3")

    def test_strips_a_word_prefix(self) -> None:
        """A non-`v` prefix must stay outside the version, or the bump 404s.

        Taking the whole tag as the version left it hard-coded in the asset
        filename, so the next bump rewrote the tag in the URL while still asking
        for the previous file.
        """
        self.assertEqual(ac.version_from_tag("release-1.2.3"), "1.2.3")
        self.assertEqual(ac.version_from_tag("app/2024.01.15"), "2024.01.15")

    def test_keeps_a_bare_version(self) -> None:
        self.assertEqual(ac.version_from_tag("1.2.3"), "1.2.3")

    def test_keeps_a_prerelease_suffix(self) -> None:
        self.assertEqual(ac.version_from_tag("v10.0.0-beta.1"), "10.0.0-beta.1")

    def test_returns_a_digitless_tag_unchanged(self) -> None:
        self.assertEqual(ac.version_from_tag("nightly"), "nightly")

    def test_prefix_survives_templating(self) -> None:
        version = ac.version_from_tag("release-1.2.3")
        self.assertEqual(ac.templatize("release-1.2.3", version),
                         "release-#{version}")
        self.assertEqual(ac.templatize("App-1.2.3.dmg", version),
                         "App-#{version}.dmg")


class PkgStanzaTest(unittest.TestCase):
    def test_pkg_emits_an_uninstall_stanza(self) -> None:
        """`brew audit --cask --strict`: pkg stanzas require an uninstall stanza."""
        stanza, _ = ac.stanza_for("App-#{version}.pkg", "App-1.2.3.pkg", "app",
                                  "com.example.app")
        self.assertIn('pkg "App-#{version}.pkg"', stanza)
        self.assertIn('uninstall pkgutil: "com.example.app"', stanza)

    def test_pkg_without_an_id_is_refused(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            ac.stanza_for("App-#{version}.pkg", "App-1.2.3.pkg", "app", None)
        self.assertIn("--pkg-id", str(caught.exception))

    def test_app_bundle_needs_no_pkg_id(self) -> None:
        stanza, hint = ac.stanza_for("App-#{version}.dmg", "App-1.2.3.dmg", "app")
        self.assertEqual(stanza, '  app "app.app"')
        self.assertIn("guess", hint)



class ArchTest(unittest.TestCase):
    def test_detects_a_single_architecture(self) -> None:
        self.assertEqual(ac.arch_for("App-arm64.dmg"), "arm64")
        self.assertEqual(ac.arch_for("App-aarch64.zip"), "arm64")
        self.assertEqual(ac.arch_for("App-x86_64.pkg"), "x86_64")
        self.assertEqual(ac.arch_for("App-amd64.dmg"), "x86_64")

    def test_universal_and_unmarked_assets_are_unconstrained(self) -> None:
        self.assertIsNone(ac.arch_for("App.dmg"))
        self.assertIsNone(ac.arch_for("App-universal.dmg"))
        # Naming both is a universal build, not a contradiction to guess at.
        self.assertIsNone(ac.arch_for("App-intel-arm64.dmg"))

    def test_arch_reaches_the_rendered_cask(self) -> None:
        cask = ac.render("tok", "Repo", "1.0", "sha", "https://u", "Desc",
                         "https://h", '  app "T.app"', "arm64")
        self.assertIn("  depends_on arch: :arm64", cask)

    def test_no_arch_stanza_when_unconstrained(self) -> None:
        cask = ac.render("tok", "Repo", "1.0", "sha", "https://u", "Desc",
                         "https://h", '  app "T.app"', None)
        self.assertNotIn("depends_on arch:", cask)


class EncodedUrlTest(unittest.TestCase):
    def test_percent_encoding_survives_templating(self) -> None:
        """The API URL is used as-is so it matches the checksummed download."""
        url = "https://github.com/o/r/releases/download/v1.2.3/My%20App-1.2.3.dmg"
        self.assertEqual(
            ac.templatize(url, "1.2.3"),
            "https://github.com/o/r/releases/download/v#{version}/"
            "My%20App-#{version}.dmg",
        )


if __name__ == "__main__":
    unittest.main()
