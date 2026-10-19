"""Classify how a producer checkout dispatches to its tap."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _workflows(root: Path) -> list[str]:
    return [path.read_text() for path in sorted((root / ".github/workflows").glob("*.y*ml"))]


def _dispatches_to(text: str, tap: str) -> bool:
    """True when ``text`` posts a dispatch to ``tap`` by ``gh api`` or by action."""
    escaped = re.escape(tap)
    return bool(
        re.search(rf"repos/{escaped}/dispatches", text)
        or re.search(rf"repository:\s*['\"]?{escaped}['\"]?\s*$", text, re.MULTILINE)
    )


def _from_copier_pyproject(root: Path) -> bool:
    answers = root / ".copier-answers.yml"
    return answers.is_file() and bool(
        re.search(r"^_src_path:\s*\S*copier-pyproject(?:\.git)?\s*$", answers.read_text(), re.MULTILINE)
    )


def classify(root: Path, tap: str) -> str:
    """Return how the producer dispatches to ``tap``.

    ``standard-job`` and ``other-dispatch`` describe what the workflows send. With
    neither, a producer rendered from copier-pyproject is ``template-owned``: the
    template renders the job, so it is enabled there. Anything else is ``none``.
    """
    workflows = _workflows(root)
    if any(re.search(r"^  bump-homebrew:", text, re.MULTILINE) for text in workflows):
        return "standard-job"
    if any(_dispatches_to(text, tap) for text in workflows):
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
