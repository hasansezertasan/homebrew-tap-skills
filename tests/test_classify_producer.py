"""Tests for classifying how a producer checkout dispatches to its tap."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/homebrew-producer-dispatch/scripts"),
)

import classify_producer  # noqa: E402

TAP = "hasansezertasan/homebrew-tap"

STANDARD_RELEASE = """\
name: Release
on:
  workflow_dispatch:
jobs:
  bump-homebrew:
    name: Bump Homebrew formula
    needs: [release-please, finalize-release]
    runs-on: ubuntu-latest
    steps:
      - run: |
          gh api repos/hasansezertasan/homebrew-tap/dispatches \\
            --method POST -f event_type=update-formula
"""


def producer(files: dict[str, str]) -> tempfile.TemporaryDirectory[str]:
    tmp = tempfile.TemporaryDirectory()
    for relative, content in files.items():
        path = Path(tmp.name) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return tmp


class ClassifyTest(unittest.TestCase):
    def test_release_workflow_with_the_standard_job(self) -> None:
        with producer({".github/workflows/release.yml": STANDARD_RELEASE}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "standard-job")

    def test_a_different_workflow_that_dispatches_to_this_tap(self) -> None:
        for body in (
            "jobs:\n  notify:\n    steps:\n      - run: gh api repos/hasansezertasan/homebrew-tap/dispatches -f event_type=update-formula\n",
            "jobs:\n  notify:\n    steps:\n      - uses: peter-evans/repository-dispatch@v3\n"
            "        with:\n          repository: hasansezertasan/homebrew-tap\n",
        ):
            with self.subTest(body=body), producer({".github/workflows/ship.yml": body}) as root:
                self.assertEqual(classify_producer.classify(Path(root), TAP), "other-dispatch")

    def test_a_dispatch_to_another_tap_is_not_this_one(self) -> None:
        body = "jobs:\n  notify:\n    steps:\n      - run: gh api repos/acme/homebrew-tools/dispatches\n"
        with producer({".github/workflows/ship.yml": body}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "none")

    def test_copier_pyproject_producer_without_a_dispatch_is_template_owned(self) -> None:
        answers = (
            "# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY\n---\n"
            "_commit: v1.13.1\n"
            "_src_path: https://github.com/hasansezertasan/copier-pyproject.git\n"
            "include_homebrew: false\n"
        )
        with producer({".copier-answers.yml": answers, ".github/workflows/release.yml": "jobs: {}\n"}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "template-owned")

    def test_another_copier_template_is_not_the_owner(self) -> None:
        answers = "_commit: v1\n_src_path: https://github.com/acme/other-template.git\n"
        with producer({".copier-answers.yml": answers}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "none")

    def test_the_standard_job_wins_over_template_ownership(self) -> None:
        answers = "_src_path: https://github.com/hasansezertasan/copier-pyproject.git\n"
        files = {".copier-answers.yml": answers, ".github/workflows/release.yml": STANDARD_RELEASE}
        with producer(files) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "standard-job")

    def test_the_job_may_be_indented_differently(self) -> None:
        head, jobs = STANDARD_RELEASE.split("jobs:\n")
        body = head + "jobs:\n" + "".join(f"  {line}" for line in jobs.splitlines(keepends=True))
        with producer({".github/workflows/release.yml": body}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "standard-job")

    def test_the_standard_job_for_another_tap_is_not_wired_to_this_one(self) -> None:
        body = STANDARD_RELEASE.replace("hasansezertasan/homebrew-tap", "acme/homebrew-tools")
        with producer({".github/workflows/release.yml": body}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "other-tap-job")

    def test_a_second_dispatch_beside_the_standard_job_is_a_duplicate(self) -> None:
        ship = "jobs:\n  notify:\n    steps:\n      - run: gh api repos/hasansezertasan/homebrew-tap/dispatches\n"
        files = {".github/workflows/release.yml": STANDARD_RELEASE, ".github/workflows/ship.yml": ship}
        with producer(files) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "duplicate-dispatch")

    def test_checking_out_the_tap_is_not_a_dispatch(self) -> None:
        body = (
            "jobs:\n  docs:\n    steps:\n      - uses: actions/checkout@v4\n"
            "        with:\n          repository: hasansezertasan/homebrew-tap\n"
        )
        with producer({".github/workflows/docs.yml": body}) as root:
            self.assertEqual(classify_producer.classify(Path(root), TAP), "none")


class MainTest(unittest.TestCase):
    def test_prints_the_classification(self) -> None:
        out = io.StringIO()
        with producer({".github/workflows/release.yml": STANDARD_RELEASE}) as root:
            with contextlib.redirect_stdout(out):
                code = classify_producer.main([root, "--tap", TAP])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "standard-job\n")


if __name__ == "__main__":
    unittest.main()
