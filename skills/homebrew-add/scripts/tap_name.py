"""Resolve the Homebrew tap name for this repository."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def from_remote(remote: str) -> str | None:
    """Convert a GitHub remote URL to ``owner/tap`` notation."""
    match = re.fullmatch(
        r"(?:(?:https?|ssh|git)://(?:[^@/]+@)?|(?:[a-zA-Z0-9_.-]+@)?)github\.com[/:]"
        r"([^/]+)/([^/#?]+?)(?:\.git)?/?",
        remote.strip(),
    )
    if not match:
        return None
    owner, repository = match.groups()
    return f"{owner}/{repository.removeprefix('homebrew-')}"


def tap_root(tap_dir: str | None) -> Path:
    """Return the tap checkout to edit.

    The scaffolders ship in a plugin, so the tap is not this script's own
    location: it is ``--tap-dir``, then ``HOMEBREW_TAP_DIR``, then the working
    directory. A tap has a ``Formula/`` or ``Casks/`` directory.
    """
    root = Path(tap_dir or os.environ.get("HOMEBREW_TAP_DIR") or Path.cwd()).resolve()
    if not ((root / "Formula").is_dir() or (root / "Casks").is_dir()):
        sys.exit(f"error: {root} has no Formula/ or Casks/ directory; run from a tap "
                 "checkout or pass --tap-dir")
    return root


def resolve(repo_root: Path) -> str | None:
    """Resolve a tap override or infer it from the ``origin`` remote."""
    if override := os.environ.get("HOMEBREW_TAP"):
        return override
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return from_remote(remote)
