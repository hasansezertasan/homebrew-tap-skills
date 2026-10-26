#!/usr/bin/env python3
"""Scaffold a Homebrew formula that builds a Rust CLI from a GitHub release tag.

Reads a GitHub repo's latest release and its ``Cargo.toml`` at that tag, downloads
the tag's source archive to compute the checksum, and writes ``Formula/<name>.rb``
following this tap's conventions: a ``cargo install`` build (``std_cargo_args``),
a ``github_latest`` livecheck and a ``--version`` smoke test. The formula builds
from source, so Homebrew can bottle it and it runs on every platform Cargo
supports; no per-architecture assets are involved.

Standard library only. Companion to ``add_formula.py`` (PyPI) and ``add_cask.py``
(prebuilt apps). Run it from the tap checkout, or pass ``--tap-dir`` / set
``HOMEBREW_TAP_DIR``.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
from pathlib import Path

import url_fetch
from add_cask import clean_desc, parse_repo, version_from_tag
from add_formula import _rb_str, class_name, is_spdx_expression, normalize
from tap_name import resolve as resolve_tap
from tap_name import tap_root

GITHUB_API = "https://api.github.com"

# `brew audit --strict` rejects a desc this long or longer.
MAX_DESC = 80


def fetch_json(url: str) -> dict:
    """Fetch and decode a JSON document from the GitHub API, failing loudly."""
    return url_fetch.get_json(url, accept="application/vnd.github+json")


def fetch_text(url: str) -> str:
    """Fetch a text file (``Cargo.toml``) at a tag."""
    with url_fetch.open_url(url, accept="text/plain") as response:
        return response.read().decode("utf-8")


def sha256_of(url: str) -> str:
    """Download a source archive and return its sha256, streaming to bounded memory."""
    print(f"==> Downloading {url} to compute sha256", file=sys.stderr)
    digest = hashlib.sha256()
    with url_fetch.open_url(url, accept="application/octet-stream") as response:
        for chunk in iter(lambda: response.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reachable(url: str) -> bool:
    """Whether a homepage answers; ``brew audit --online`` rejects one that does not."""
    # A repo owner sets `homepage` as free text: restrict to http(s) so `file:` or a
    # scheme-less value is never "reachable", and treat any malformed one as dead.
    if not url.lower().startswith(("http://", "https://")):
        return False
    try:
        with url_fetch.open_url(url, accept="text/html"):
            return True
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException):
        return False


def implicit_binaries(owner: str, repo: str, tag: str, crate_dir: str,
                      package_name: str) -> list[str]:
    """Binaries Cargo discovers without a ``[[bin]]`` table.

    ``src/main.rs`` builds one named after the package; each ``src/bin/<x>.rs`` or
    ``src/bin/<x>/main.rs`` builds ``<x>``. Read from the tagged tree, since the
    manifest alone cannot tell.
    """
    base = f"{GITHUB_API}/repos/{owner}/{repo}/contents/"
    prefix = f"{crate_dir}/" if crate_dir else ""

    def listing(path: str) -> list[dict]:
        try:
            result = fetch_json(f"{base}{path}?ref={tag}")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return []
            raise
        return result if isinstance(result, list) else []

    found = [package_name] if any(
        e["name"] == "main.rs" for e in listing(f"{prefix}src")) else []
    for entry in listing(f"{prefix}src/bin"):
        if entry["type"] == "file" and entry["name"].endswith(".rs"):
            found.append(entry["name"].removesuffix(".rs"))
        elif entry["type"] == "dir" and any(
                e["name"] == "main.rs"
                for e in listing(f"{prefix}src/bin/{entry['name']}")):
            found.append(entry["name"])
    return found


def binary_names(manifest: dict, package_name: str,
                 implicit: list[str] | None = None) -> list[str]:
    """Return the executables a crate builds: explicit ``[[bin]]`` plus discovered ones.

    ``implicit`` comes from :func:`implicit_binaries`. With neither, fall back to
    the package name, the ``src/main.rs`` default.
    """
    names = [b["name"] for b in manifest.get("bin", []) if b.get("name")]
    names += [n for n in (implicit or []) if n not in names]
    return names or [package_name]


def inherited(package: dict, key: str, workspace_package: dict) -> str:
    """Resolve a package string field, following ``<key>.workspace = true``.

    A workspace member may inherit ``license`` or ``description`` from the root's
    ``[workspace.package]``; ``tomllib`` then yields ``{"workspace": True}`` rather
    than a string. Anything that does not resolve to a string is treated as absent.
    """
    value = package.get(key)
    if isinstance(value, dict) and value.get("workspace"):
        value = workspace_package.get(key)
    return value.strip() if isinstance(value, str) else ""


def spdx_from_github(meta: dict, manifest: dict,
                     workspace_package: dict | None = None) -> str:
    """Prefer the manifest's SPDX ``license``, then GitHub's detection.

    GitHub reports ``NOASSERTION`` for a license it cannot classify; that is not a
    usable value, so the TODO marker (which ``brew audit --strict`` rejects) forces
    a human to set it.
    """
    declared = inherited(manifest.get("package", {}), "license", workspace_package or {})
    if declared and is_spdx_expression(declared):
        return declared
    detected = ((meta.get("license") or {}).get("spdx_id") or "").strip()
    if detected and detected != "NOASSERTION" and is_spdx_expression(detected):
        return detected
    return "TODO-set-SPDX-license"


def default_test_command(binary: str) -> str:
    """Best-guess smoke test: nearly every clap/argh CLI answers ``--version``.

    A TUI or daemon may not exit on ``--version``; override with ``--test-command``.
    """
    return f"#{{bin}}/{binary} --version"


def license_literal(license_id: str) -> str:
    """Return the Ruby argument for ``license``.

    Homebrew's DSL has no string form for compound expressions: ``MIT OR
    Apache-2.0`` must be ``any_of: ["MIT", "Apache-2.0"]``. Handle a flat
    ``OR``/``AND`` list; anything more intricate (parentheses, ``WITH``, mixed
    operators) keeps the verbatim string so ``brew audit`` flags it for a human.
    """
    tokens = license_id.split()
    operators = {t.upper() for t in tokens[1::2]}
    if len(tokens) > 1 and operators in ({"OR"}, {"AND"}) and not any(
            "(" in t or ")" in t for t in tokens):
        key = "any_of" if operators == {"OR"} else "all_of"
        ids = ", ".join(f'"{_rb_str(t)}"' for t in tokens[::2])
        return f"{key}: [{ids}]"
    return f'"{_rb_str(license_id)}"'


def render(name: str, url: str, sha: str, desc: str, homepage: str,
           license_id: str, test_command: str, path: str | None = None) -> str:
    """Render the Ruby formula source."""
    # Escape for the double-quoted Ruby literal; `#{bin}` interpolation stays live.
    test_command = test_command.replace("\\", "\\\\").replace('"', '\\"')
    cargo_args = f'std_cargo_args(path: "{_rb_str(path)}")' if path else "std_cargo_args"
    return "\n".join([
        f"class {class_name(name)} < Formula",
        f'  desc "{_rb_str(desc)}"',
        f'  homepage "{_rb_str(homepage)}"',
        f'  url "{_rb_str(url)}"',
        f'  sha256 "{_rb_str(sha)}"',
        f"  license {license_literal(license_id)}",
        "",
        "  livecheck do",
        "    url :stable",
        "    strategy :github_latest",
        "  end",
        "",
        '  depends_on "rust" => :build',
        "",
        "  def install",
        f'    system "cargo", "install", *{cargo_args}',
        "  end",
        "",
        "  test do",
        f'    assert_match version.to_s, shell_output("{test_command}")',
        "  end",
        "end",
        "",
    ])


def run_checks(repo: Path, name: str, tap: str) -> None:
    """Copy the formula into the active tap and run audit, install, and test."""
    user, _, short = tap.partition("/")
    brew_repo = subprocess.run(
        ["brew", "--repository"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    tap_formula = Path(brew_repo) / "Library" / "Taps" / user / \
        f"homebrew-{short}" / "Formula" / f"{name}.rb"
    if not tap_formula.parent.is_dir():
        sys.exit(f"error: tap '{tap}' is not tapped at {tap_formula.parent}; run "
                 f"`brew tap {tap} {repo}` first")
    source = repo / "Formula" / f"{name}.rb"
    staged = source.resolve() != tap_formula.resolve()
    previous = tap_formula.read_bytes() if staged and tap_formula.exists() else None
    if staged:
        shutil.copy(source, tap_formula)
    ref = f"{tap}/{name}"
    installed = subprocess.run(["brew", "list", "--formula", ref],
                               capture_output=True).returncode == 0
    build = "reinstall" if installed else "install"
    try:
        for cmd in (
            ["brew", "audit", "--strict", "--online", ref],
            ["brew", build, "--build-from-source", ref],
            ["brew", "test", ref],
        ):
            print(f"\n==> {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
    finally:
        if previous is not None:
            tap_formula.write_bytes(previous)
        elif staged:
            tap_formula.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", help="GitHub repo as 'owner/repo' or a github.com URL")
    parser.add_argument("--name",
                        help="override the formula name (default: the binary name)")
    parser.add_argument("--path", metavar="DIR",
                        help="crate directory inside a workspace (passed as "
                             "`path:` to std_cargo_args)")
    parser.add_argument("--test-command", metavar="CMD",
                        help="smoke test command for `test do` (default: "
                             "'#{bin}/<binary> --version')")
    parser.add_argument("--check", action="store_true",
                        help="audit, build-from-source, and test the result")
    parser.add_argument("--tap", help="tap name used by --check (default: infer from origin)")
    parser.add_argument("--tap-dir",
                        help="tap checkout to edit (default: HOMEBREW_TAP_DIR or the "
                             "current directory)")
    args = parser.parse_args()

    owner, repo = parse_repo(args.repo)
    try:
        meta = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}")
        release = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            sys.exit(f"error: {owner}/{repo} not found or has no published "
                     "(non-draft, non-prerelease) 'latest' release")
        raise
    tag = release["tag_name"]
    version = version_from_tag(tag)

    manifest_path = f"{args.path.strip('/')}/Cargo.toml" if args.path else "Cargo.toml"
    try:
        manifest = tomllib.loads(fetch_text(
            f"https://raw.githubusercontent.com/{owner}/{repo}/{tag}/{manifest_path}"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            sys.exit(f"error: no {manifest_path} at tag {tag}; this is not a Rust "
                     "crate (or pass --path for a workspace member)")
        raise
    package = manifest.get("package")
    if not package:
        sys.exit(f"error: {manifest_path} has no [package] (a workspace root?); "
                 "pass --path to the member crate that builds the CLI")

    # Fetch the workspace root only when a field is inherited from it. A member's
    # root is the repo's top-level manifest in the common layout.
    workspace_package: dict = {}
    if any(isinstance(package.get(k), dict) for k in ("license", "description")):
        root_manifest = manifest if not args.path else tomllib.loads(fetch_text(
            f"https://raw.githubusercontent.com/{owner}/{repo}/{tag}/Cargo.toml"))
        workspace_package = root_manifest.get("workspace", {}).get("package", {})
    binaries = binary_names(manifest, package["name"], implicit_binaries(
        owner, repo, tag, (args.path or "").strip("/"), package["name"]))
    name = normalize(args.name or binaries[0])
    if "/" in name or "\\" in name:
        sys.exit(f"error: --name {args.name!r} must not contain path separators")
    try:
        class_name(name)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    if len(binaries) > 1:
        print(f"warning: the crate builds several binaries ({', '.join(binaries)}); "
              f"the smoke test uses {binaries[0]!r} — check the others install",
              file=sys.stderr)

    # GitHub's tag archive is what `brew bump-formula-pr` rewrites on a release; the
    # tag is percent-safe for the characters release tooling emits.
    url = f"https://github.com/{owner}/{repo}/archive/refs/tags/{tag}.tar.gz"
    sha = sha256_of(url)
    desc = clean_desc(inherited(package, "description", workspace_package)
                      or meta.get("description") or "TODO-set-description")
    repo_url = meta.get("html_url") or f"https://github.com/{owner}/{repo}"
    homepage = meta.get("homepage") or repo_url
    if homepage != repo_url and not reachable(homepage):
        print(f"warning: homepage {homepage} is not reachable; using {repo_url}",
              file=sys.stderr)
        homepage = repo_url
    license_id = spdx_from_github(meta, manifest, workspace_package)
    if len(desc) >= MAX_DESC:
        print(f"warning: desc is {len(desc)} characters; `brew audit --strict` "
              f"requires fewer than {MAX_DESC}. Shorten it by hand",
              file=sys.stderr)
    test_command = args.test_command or default_test_command(binaries[0])

    root = tap_root(args.tap_dir)
    out = root / "Formula" / f"{name}.rb"
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        sys.exit(f"error: {out} already exists; refusing to overwrite it")
    out.write_text(render(name, url, sha, desc, homepage, license_id,
                          test_command, args.path))
    print(f"==> Wrote {out.relative_to(root)} (version {version}, builds with cargo)")
    if license_id.startswith("TODO"):
        print("warning: no SPDX license found; set `license` by hand", file=sys.stderr)
    if "rust-version" in package:
        print(f"note: the crate needs Rust >= {package['rust-version']}; confirm "
              "Homebrew's `rust` formula is at least that new", file=sys.stderr)

    tap = args.tap or resolve_tap(root)
    if args.check:
        if not tap:
            sys.exit("error: cannot infer the tap name; pass --tap owner/tap or set "
                     "HOMEBREW_TAP")
        run_checks(root, name, tap)
    else:
        ref = f"{tap}/{name}" if tap else f"<owner>/<tap>/{name}"
        print(f"\nNext: brew audit --strict --online {ref}  "
              "(or re-run with --check)")


if __name__ == "__main__":
    main()
