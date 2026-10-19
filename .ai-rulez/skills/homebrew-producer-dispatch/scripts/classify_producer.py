"""Classify how a producer checkout dispatches to its tap."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _workflows(root: Path) -> list[str]:
    return [path.read_text() for path in sorted((root / ".github/workflows").glob("*.y*ml"))]


def _split_bump_job(text: str) -> tuple[str | None, str]:
    """Split ``text`` into its ``bump-homebrew`` job block, if any, and the rest."""
    lines = text.splitlines(keepends=True)
    for start, line in enumerate(lines):
        match = re.match(r"(\s+)bump-homebrew:\s*$", line)
        if not match:
            continue
        indent = len(match.group(1))
        end = start + 1
        while end < len(lines) and (
            not lines[end].strip() or len(lines[end]) - len(lines[end].lstrip()) > indent
        ):
            end += 1
        return "".join(lines[start:end]), "".join(lines[:start] + lines[end:])
    return None, text


def _dispatches_to(text: str, tap: str) -> bool:
    """True when ``text`` posts a dispatch to ``tap`` by ``gh api`` or by action."""
    escaped = re.escape(tap)
    return bool(
        re.search(rf"repos/{escaped}/dispatches", text)
        or (
            "repository-dispatch" in text
            and re.search(rf"repository:\s*['\"]?{escaped}['\"]?\s*$", text, re.MULTILINE)
        )
    )


def _from_copier_pyproject(root: Path) -> bool:
    answers = root / ".copier-answers.yml"
    pattern = r"^_src_path:\s*\S*copier-pyproject(?:\.git)?\s*$"
    return answers.is_file() and bool(re.search(pattern, answers.read_text(), re.MULTILINE))


def classify(root: Path, tap: str) -> str:
    """Return how the producer dispatches to ``tap``.

    - ``standard-job``: a ``bump-homebrew`` job dispatches to ``tap``, and nothing else does.
    - ``duplicate-dispatch``: that job exists and another workflow also dispatches to ``tap``.
    - ``other-tap-job``: a ``bump-homebrew`` job exists but dispatches elsewhere, so the
      job id is taken.
    - ``other-dispatch``: some other workflow dispatches to ``tap``.
    - ``template-owned``: none of those, and the producer is rendered from copier-pyproject,
      whose template renders the job, so it is enabled there.
    - ``none``: anything else.
    """
    jobs: list[str] = []
    elsewhere: list[str] = []
    for text in _workflows(root):
        job, rest = _split_bump_job(text)
        if job is not None:
            jobs.append(job)
        elsewhere.append(rest)
    other_dispatch = any(_dispatches_to(text, tap) for text in elsewhere)
    if any(_dispatches_to(job, tap) for job in jobs):
        return "duplicate-dispatch" if other_dispatch else "standard-job"
    if jobs:
        return "other-tap-job"
    if other_dispatch:
        return "other-dispatch"
    if _from_copier_pyproject(root):
        return "template-owned"
    return "none"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("producer", help="a checkout of the producer repository")
    parser.add_argument("--tap", required=True, help="the tap repository, owner/homebrew-<tap>")
    args = parser.parse_args(argv)
    print(classify(Path(args.producer), args.tap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
