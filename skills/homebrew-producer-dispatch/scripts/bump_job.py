"""Render the ``bump-homebrew`` job a producer's release workflow carries."""

from __future__ import annotations

import argparse
import re
import sys

# The receiver's own check on the payload name: whole-string, no newlines.
_NAME = re.compile(r"[a-z0-9][a-z0-9._+@-]*")
_TAP = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_JOB_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
_SECRET = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_KINDS = ("formula", "cask")
DEFAULT_SECRET = "HOMEBREW_TAP_TOKEN"

_JOB = """\
  bump-homebrew:
    name: Bump Homebrew {kind}
    needs: [{needs}]
    if: ${{{{ {gate} }}}}
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions: {{}}
    steps:
      - name: Dispatch the tap update
        env:
          # PAT with Contents: write on the tap repo (NOT the repo GITHUB_TOKEN,
          # which cannot POST a cross-repo dispatch). Absent → skip, never fail.
          GH_TOKEN: ${{{{ secrets.{secret} }}}}
{version_env}        run: |
          if [ -z "${{GH_TOKEN:-}}" ]; then
            echo "::warning::{secret} not set; skipping Homebrew bump"
            exit 0
          fi
          echo "Dispatching update-{kind} for {name}{version_echo}"
          gh api repos/{tap}/dispatches \\
            --method POST \\
            -f event_type=update-{kind} \\
            -f 'client_payload[{kind}]={name}'{version_field}
"""
_VERSION_ENV = "          VERSION: ${{{{ {expr} }}}}\n"
_VERSION_FIELD = ' \\\n            -f "client_payload[version]=$VERSION"'


def render(
    *,
    kind: str,
    name: str,
    tap: str,
    needs: list[str],
    gate: str,
    version_expr: str | None,
    secret: str = DEFAULT_SECRET,
) -> str:
    """Return the job text, indented to sit under a workflow's ``jobs:`` key."""
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, not {kind!r}")
    if not _NAME.fullmatch(name):
        raise ValueError(f"invalid {kind} name: {name!r}")
    if not _TAP.fullmatch(tap):
        raise ValueError(f"tap must be owner/repo, not {tap!r}")
    if not _SECRET.fullmatch(secret):
        raise ValueError(f"secret must be a GitHub secret name, not {secret!r}")
    if not needs or not all(_JOB_ID.fullmatch(job) for job in needs):
        raise ValueError(f"needs must be one or more job ids, not {needs!r}")
    expressions = {"gate": gate}
    if version_expr is not None:
        expressions["version_expr"] = version_expr
    for field, value in expressions.items():
        if not value.strip() or "\n" in value or "{{" in value or "}}" in value:
            raise ValueError(f"{field} must be one expression without braces: {value!r}")
        if " #" in value or ": " in value:
            raise ValueError(f"{field} must not contain ' #' or ': ', which break YAML: {value!r}")
    with_version = version_expr is not None
    return _JOB.format(
        kind=kind,
        name=name,
        tap=tap,
        secret=secret,
        needs=", ".join(needs),
        gate=gate,
        version_env=_VERSION_ENV.format(expr=version_expr) if with_version else "",
        version_echo=" $VERSION" if with_version else "",
        version_field=_VERSION_FIELD if with_version else "",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=_KINDS)
    parser.add_argument("name", help="formula or cask token")
    parser.add_argument("--tap", required=True, help="the tap repository, owner/homebrew-<tap>")
    parser.add_argument("--needs", required=True, help="comma-separated release job ids")
    parser.add_argument("--gate", required=True, help="the job's `if` expression, without ${{ }}")
    parser.add_argument(
        "--secret",
        default=DEFAULT_SECRET,
        help=f"the producer's Actions secret holding the tap token (default {DEFAULT_SECRET})",
    )
    parser.add_argument(
        "--version-expr",
        help="expression holding the released version; omit to leave `version` out of the payload",
    )
    args = parser.parse_args(argv)
    try:
        sys.stdout.write(
            render(
                kind=args.kind,
                name=args.name,
                tap=args.tap,
                needs=[job.strip() for job in args.needs.split(",")],
                gate=args.gate,
                version_expr=args.version_expr,
                secret=args.secret,
            )
        )
    except ValueError as error:
        sys.exit(f"error: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
