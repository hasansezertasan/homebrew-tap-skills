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
            not lines[end].strip()
            or lines[end].lstrip().startswith("#")
            or len(lines[end]) - len(lines[end].lstrip()) > indent
        ):
            end += 1
        return "".join(lines[start:end]), "".join(lines[:start] + lines[end:])
    return None, text


def _dispatch_steps(text: str) -> list[str]:
    """Return the block of each ``repository-dispatch`` action step in ``text``."""
    lines = text.splitlines(keepends=True)
    blocks = []
    for start, line in enumerate(lines):
        match = re.search(r"uses:\s*\S*repository-dispatch", line)
        if not match:
            continue
        indent = line.index("uses:")
        end = start + 1
        while end < len(lines) and (
            not lines[end].strip()
            or lines[end].lstrip().startswith("#")
            or len(lines[end]) - len(lines[end].lstrip()) >= indent
        ):
            end += 1
        blocks.append("".join(lines[start:end]))
    return blocks


def _dispatches_to(text: str, tap: str) -> bool:
    """True when ``text`` posts a dispatch to ``tap`` by ``gh api`` or by action."""
    escaped = re.escape(tap)
    if re.search(rf"repos/{escaped}/dispatches", text, re.IGNORECASE):
        return True
    pattern = rf"repository:\s*['\"]?{escaped}['\"]?\s*(?:#.*)?$"
    return any(
        re.search(pattern, step, re.MULTILINE | re.IGNORECASE) for step in _dispatch_steps(text)
    )


def _from_copier_pyproject(root: Path) -> bool:
    answers = root / ".copier-answers.yml"
    pattern = r"""^_src_path:\s*["']?(?:[^\s"']*[/:])?copier-pyproject(?:\.git)?["']?\s*$"""
    return answers.is_file() and bool(re.search(pattern, answers.read_text(), re.MULTILINE))


def classify(root: Path, tap: str, kind: str | None = None) -> str:
    """Return how the producer dispatches to ``tap``.

    - ``standard-job``: a ``bump-homebrew`` job dispatches to ``tap``, and nothing else does.
    - ``other-kind-job``: that job dispatches the other kind than ``kind`` (``formula`` or
      ``cask``), so the job id is taken. Without ``kind`` the event type is not compared.
    - ``duplicate-dispatch``: more than one workflow job or step dispatches to ``tap``.
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
    wired = [job for job in jobs if _dispatches_to(job, tap)]
    if wired:
        if other_dispatch or len(wired) > 1:
            return "duplicate-dispatch"
        if kind and not re.search(rf"event[_-]type(?:=|:\s*)['\"]?update-{kind}\b", wired[0]):
            return "other-kind-job"
        return "standard-job"
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
    parser.add_argument("--kind", choices=("formula", "cask"), help="what the user wants wired")
    args = parser.parse_args(argv)
    print(classify(Path(args.producer), args.tap, args.kind))
    return 0


if __name__ == "__main__":
    sys.exit(main())
