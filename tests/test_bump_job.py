"""Tests for rendering the producer's bump-homebrew job."""

from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/homebrew-producer-dispatch/scripts"),
)

import bump_job  # noqa: E402

# The job as hwid's release.yml carries it, which copier-pyproject renders.
HWID_FORMULA_JOB = """\
  bump-homebrew:
    name: Bump Homebrew formula
    needs: [release-please, finalize-release]
    if: ${{ needs.release-please.outputs.release_created == 'true' }}
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions: {}
    steps:
      - name: Dispatch the tap update
        env:
          # PAT with Contents: write on the tap repo (NOT the repo GITHUB_TOKEN,
          # which cannot POST a cross-repo dispatch). Absent → skip, never fail.
          GH_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
          VERSION: ${{ needs.release-please.outputs.version }}
        run: |
          if [ -z "${GH_TOKEN:-}" ]; then
            echo "::warning::HOMEBREW_TAP_TOKEN not set; skipping Homebrew bump"
            exit 0
          fi
          echo "Dispatching update-formula for hwid $VERSION"
          gh api repos/hasansezertasan/homebrew-tap/dispatches \\
            --method POST \\
            -f event_type=update-formula \\
            -f 'client_payload[formula]=hwid' \\
            -f "client_payload[version]=$VERSION"
"""

# The job as keycast's release.yml carries it: a cask, with a prerelease condition.
KEYCAST_CASK_JOB = """\
  bump-homebrew:
    name: Bump Homebrew cask
    needs: [release-please, finalize-release]
    if: ${{ needs.release-please.outputs.release_created == 'true' && needs.release-please.outputs.is_prerelease != 'true' }}
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions: {}
    steps:
      - name: Dispatch the tap update
        env:
          # PAT with Contents: write on the tap repo (NOT the repo GITHUB_TOKEN,
          # which cannot POST a cross-repo dispatch). Absent → skip, never fail.
          GH_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
          VERSION: ${{ needs.release-please.outputs.version }}
        run: |
          if [ -z "${GH_TOKEN:-}" ]; then
            echo "::warning::HOMEBREW_TAP_TOKEN not set; skipping Homebrew bump"
            exit 0
          fi
          echo "Dispatching update-cask for keycast $VERSION"
          gh api repos/hasansezertasan/homebrew-tap/dispatches \\
            --method POST \\
            -f event_type=update-cask \\
            -f 'client_payload[cask]=keycast' \\
            -f "client_payload[version]=$VERSION"
"""


class RenderTest(unittest.TestCase):
    def test_formula_matches_the_standard_job(self) -> None:
        job = bump_job.render(
            kind="formula",
            name="hwid",
            tap="hasansezertasan/homebrew-tap",
            needs=["release-please", "finalize-release"],
            gate="needs.release-please.outputs.release_created == 'true'",
            version_expr="needs.release-please.outputs.version",
        )
        self.assertEqual(job, HWID_FORMULA_JOB)


class KindAndVersionTest(unittest.TestCase):
    def test_cask_matches_the_standard_job(self) -> None:
        job = bump_job.render(
            kind="cask",
            name="keycast",
            tap="hasansezertasan/homebrew-tap",
            needs=["release-please", "finalize-release"],
            gate=(
                "needs.release-please.outputs.release_created == 'true' && "
                "needs.release-please.outputs.is_prerelease != 'true'"
            ),
            version_expr="needs.release-please.outputs.version",
        )
        self.assertEqual(job, KEYCAST_CASK_JOB)

    def test_a_named_secret_replaces_the_default_everywhere(self) -> None:
        job = bump_job.render(
            kind="formula",
            name="hwid",
            tap="hasansezertasan/homebrew-tap",
            needs=["publish"],
            gate="true",
            version_expr=None,
            secret="ACME_TAP_PAT",
        )
        self.assertIn("GH_TOKEN: ${{ secrets.ACME_TAP_PAT }}", job)
        self.assertIn("ACME_TAP_PAT not set; skipping Homebrew bump", job)
        self.assertNotIn("HOMEBREW_TAP_TOKEN", job)

    def test_without_a_version_the_payload_carries_only_the_name(self) -> None:
        job = bump_job.render(
            kind="formula",
            name="hwid",
            tap="hasansezertasan/homebrew-tap",
            needs=["publish"],
            gate="github.event_name == 'release'",
            version_expr=None,
        )
        self.assertIn("-f 'client_payload[formula]=hwid'\n", job)
        self.assertNotIn("version", job.lower())


class ValidationTest(unittest.TestCase):
    def render(self, **overrides: object) -> str:
        args: dict[str, object] = {
            "kind": "formula",
            "name": "hwid",
            "tap": "hasansezertasan/homebrew-tap",
            "needs": ["release-please", "finalize-release"],
            "gate": "needs.release-please.outputs.release_created == 'true'",
            "version_expr": "needs.release-please.outputs.version",
        }
        args.update(overrides)
        return bump_job.render(**args)  # type: ignore[arg-type]

    def test_rejects_a_name_the_receiver_would_refuse(self) -> None:
        for name in ("Hwid", "-hwid", "hw id", "hwid\nx", "hwid'; rm -rf / #"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.render(name=name)

    def test_rejects_a_tap_that_is_not_owner_repo(self) -> None:
        for tap in ("homebrew-tap", "a/b/c", "a/b c", "a/b\nx", "a/b;rm"):
            with self.subTest(tap=tap), self.assertRaises(ValueError):
                self.render(tap=tap)

    def test_rejects_a_secret_name_github_would_not_accept(self) -> None:
        for secret in ("", "1TOKEN", "GITHUB_TOKEN2 x", "tok}}", "A\nB"):
            with self.subTest(secret=secret), self.assertRaises(ValueError):
                self.render(secret=secret)

    def test_rejects_unknown_kind_and_bad_job_ids(self) -> None:
        with self.assertRaises(ValueError):
            self.render(kind="bottle")
        for needs in ([], ["a b"], ["ok", "x]\n  evil: {"]):
            with self.subTest(needs=needs), self.assertRaises(ValueError):
                self.render(needs=needs)

    def test_rejects_expressions_that_could_leave_the_expression(self) -> None:
        for field in ("gate", "version_expr"):
            for value in ("a }} b", "a\nb", "", "a == 'x' # why", "a ? b: c"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.render(**{field: value})


class MainTest(unittest.TestCase):
    def test_prints_the_job_for_the_given_arguments(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = bump_job.main(
                [
                    "formula",
                    "hwid",
                    "--tap",
                    "hasansezertasan/homebrew-tap",
                    "--needs",
                    "release-please,finalize-release",
                    "--gate",
                    "needs.release-please.outputs.release_created == 'true'",
                    "--version-expr",
                    "needs.release-please.outputs.version",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), HWID_FORMULA_JOB)

    def test_secret_option_is_passed_through(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bump_job.main(["cask", "keycast", "--tap", "a/b", "--needs", "x", "--gate", "true", "--secret", "ACME_PAT"])
        self.assertIn("secrets.ACME_PAT", out.getvalue())

    def test_exits_with_the_reason_for_an_invalid_name(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            bump_job.main(["formula", "Hwid", "--tap", "a/b", "--needs", "x", "--gate", "true"])
        self.assertIn("invalid formula name", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
