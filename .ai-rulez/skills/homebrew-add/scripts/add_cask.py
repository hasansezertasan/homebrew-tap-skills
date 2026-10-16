#!/usr/bin/env python3
"""Scaffold a Homebrew cask for a prebuilt macOS app from a GitHub release.

Reads a GitHub repo's latest release, picks a distributable artifact (``.dmg`` /
``.pkg`` / ``.zip``), computes its sha256, and writes ``Casks/<name>.rb`` following
this tap's conventions (version-templated download URL, ``github_latest`` livecheck,
an ``app``/``pkg`` stanza). Casks ship a pre-built app, so — unlike a formula —
there are no Python resources to resolve.

Standard library only — no third-party dependencies. Companion to
``add_formula.py``. Run it from the tap checkout, or pass ``--tap-dir`` / set
``HOMEBREW_TAP_DIR``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

from tap_name import resolve as resolve_tap
from tap_name import tap_root

GITHUB_API = "https://api.github.com"

# Artifact preference order when --artifact isn't given. A .dmg or .zip carries a
# .app bundle (`app` stanza); a .pkg is an installer (`pkg` stanza).
_ARTIFACT_PREFERENCE = (".dmg", ".pkg", ".zip")

# 64 zero hex digits: a syntactically valid placeholder sha256 for --seed mode.
# `brew bump-cask-pr` overwrites it (and the version) on the first real release.
_PLACEHOLDER_SHA = "0" * 64
_PLACEHOLDER_VERSION = "0.0.0"


def _request(url: str, *, accept: str = "application/vnd.github+json") -> urllib.request.Request:
    """Build a GitHub API request, authenticating from the environment if possible."""
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "homebrew-tap-add-cask")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def fetch_json(url: str) -> dict:
    """Fetch and decode a JSON document from the GitHub API, failing loudly."""
    with urllib.request.urlopen(_request(url)) as response:  # noqa: S310 - trusted host
        return json.load(response)


def normalize(name: str) -> str:
    """Normalize a repo name to its cask token (lowercase, hyphen-separated)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_repo(ref: str) -> tuple[str, str]:
    """Parse ``owner/repo`` or a GitHub URL into an ``(owner, repo)`` pair."""
    match = re.search(r"github\.com[/:]([^/]+)/([^/#?]+)", ref)
    if match:
        owner, repo = match.group(1), match.group(2)
    elif "/" in ref and ref.count("/") == 1:
        owner, repo = ref.split("/", 1)
    else:
        sys.exit(f"error: cannot parse GitHub repo from {ref!r}; pass 'owner/repo' "
                 "or a github.com URL")
    return owner, repo.removesuffix(".git")


def clean_desc(summary: str) -> str:
    """Format a repo description as a Homebrew ``desc``.

    Strips a leading article and trailing period, then capitalizes the first letter
    (``brew audit --strict`` requires a ``desc`` that starts with a capital).
    """
    # Case-insensitive: a lowercase "a "/"the " prefix is just as much a leading
    # article, and `brew audit --strict` rejects it either way.
    desc = re.sub(r"^(?:an?|the)\s+", "", (summary or "").strip().rstrip("."),
                  flags=re.IGNORECASE)
    return desc[:1].upper() + desc[1:] if desc else desc


def select_asset(assets: list[dict], wanted: str | None) -> dict:
    """Pick the release asset to package, honoring --artifact or the preference order."""
    if not assets:
        sys.exit("error: the latest release has no downloadable assets; pass --seed "
                 "to scaffold a placeholder, or --artifact once a release exists")
    if wanted:
        for asset in assets:
            if asset["name"] == wanted:
                if not asset["name"].lower().endswith(_ARTIFACT_PREFERENCE):
                    sys.exit(f"error: {wanted!r} is not a supported cask asset "
                             f"({', '.join(_ARTIFACT_PREFERENCE)})")
                return asset
        names = ", ".join(a["name"] for a in assets)
        sys.exit(f"error: no asset named {wanted!r}; available: {names}")
    for suffix in _ARTIFACT_PREFERENCE:
        matches = [a for a in assets if a["name"].lower().endswith(suffix)]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Multiple candidates of the same type usually means per-architecture
            # builds (e.g. App-arm64.dmg vs App-x64.dmg). One cask can't serve both
            # from a single url/sha, so make the choice explicit instead of guessing.
            names = ", ".join(a["name"] for a in matches)
            sys.exit(f"error: multiple {suffix} assets ({names}); pass --artifact to "
                     "pick one. Per-architecture builds need a hand-written cask with "
                     "`on_arm`/`on_intel` blocks, which this scaffolder does not emit")
    sys.exit("error: no .dmg/.pkg/.zip asset found; pass --artifact to choose one of: "
             + ", ".join(a["name"] for a in assets))


def sha256_of(url: str) -> str:
    """Download a release asset and return its sha256, streaming to bounded memory."""
    print(f"==> Downloading {url} to compute sha256", file=sys.stderr)
    digest = hashlib.sha256()
    with urllib.request.urlopen(_request(url, accept="application/octet-stream")) as response:  # noqa: S310
        for chunk in iter(lambda: response.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version_from_tag(tag: str) -> str:
    """Extract the version from a release tag, keeping any prefix out of it.

    A tag is usually the version with a decoration: ``v1.2.3``, ``release-1.2.3``,
    ``app/1.2.3``. Only the numeric part belongs in the cask's ``version``, so that
    :func:`templatize` finds it in *both* the tag and the asset filename and the
    prefix stays literal in the URL. Taking the whole tag (the old ``v``-only
    behaviour) left the version hard-coded in the asset name, so the next automated
    bump rewrote the tag in the URL while still requesting the previous filename —
    a 404. A tag with no digits has no version to extract and is returned as-is.
    """
    # Prefer a dotted version so a digit in the decoration (`app2-v1.2.3`) is not
    # taken as its start; fall back to any trailing number (`v12`).
    match = (re.search(r"\d+(?:\.\d+)+[\w.+-]*$", tag)
             or re.search(r"\d[\w.+-]*$", tag))
    return match.group(0) if match else tag


def templatize(text: str, version: str) -> str:
    """Replace literal occurrences of the version in a URL/filename with ``#{version}``.

    Warns when the version is absent: that URL segment then stays hard-coded and
    ``brew bump-cask-pr``/livecheck can't bump it on the next release.
    """
    if not version:
        return text
    if version not in text:
        print(f"warning: version {version!r} not found in {text!r}; that part of the "
              "URL won't auto-update on release bumps — verify the cask", file=sys.stderr)
    return text.replace(version, "#{version}")


def _rb_str(value: str) -> str:
    """Escape a value for a double-quoted Ruby string literal in the generated cask.

    Cask files are Ruby evaluated by ``brew audit``/``install``; an unescaped quote
    or backslash from GitHub-supplied metadata (desc, homepage, tag) would otherwise
    break out of the string literal, and ``#{...}`` would interpolate — running
    arbitrary Ruby the moment the cask is loaded.

    Because this escapes ``#{`` too, the ordering rule for anything version-templated
    is: **escape the untrusted parts first, then** :func:`templatize`, and never
    escape again downstream. A version string is digits and dots, so it survives
    escaping unchanged and templatize still finds it. Escaping afterwards would
    neutralise the ``#{version}`` marker that lets ``brew bump-cask-pr`` rewrite the
    version in one place.
    """
    return (value.replace("\\", "\\\\")
                 .replace('"', '\\"')
                 .replace("#{", "\\#{"))



def arch_for(artifact: str) -> str | None:
    """Return the cask ``arch`` symbol implied by an asset filename, if any.

    A release that ships one architecture-specific build (``App-arm64.dmg``) would
    otherwise get a cask constrained only to macOS, so Homebrew would happily
    install it on the other architecture. The returned symbol is one of
    ``VALID_ARCHES`` in Homebrew's ``cask/dsl/depends_on.rb``; ``None`` means the
    name carries no architecture marker and the cask stays unconstrained (a
    universal build, or one this cannot tell apart).
    """
    lowered = artifact.lower()
    markers = {
        "arm64": ("arm64", "aarch64", "apple-silicon", "applesilicon"),
        "x86_64": ("x86_64", "x86-64", "x64", "amd64", "intel"),
    }
    # Require non-alphanumeric boundaries so a product name that merely contains a
    # marker (``IntelliJ``) is not read as an architecture.
    found = {arch for arch, needles in markers.items()
             if any(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", lowered)
                    for needle in needles)}
    # A name mentioning both (a universal artifact) constrains nothing.
    return found.pop() if len(found) == 1 else None


def stanza_for(stanza_artifact: str, artifact: str, token: str,
               pkg_id: str | None = None) -> tuple[str, str]:
    """Return the artifact stanza(s) and a verify-hint for the given asset.

    ``stanza_artifact`` is the (version-templated) filename that matches the URL. A
    ``.pkg`` installs via a ``pkg`` stanza pinned to that templated name, plus an
    ``uninstall pkgutil:`` stanza — ``brew audit --cask --strict`` rejects a pkg
    without one ("installer and pkg stanzas require an uninstall stanza" in
    ``cask/audit.rb``), and without it Homebrew cannot remove the payload. The
    package id cannot be read from the asset without unpacking it, so it comes from
    ``--pkg-id``. A ``.dmg``/``.zip`` carries a ``.app`` bundle whose real name we
    can't know without unpacking either, so we guess ``<token>.app`` and flag it.
    """
    if artifact.lower().endswith(".pkg"):
        if not pkg_id:
            sys.exit(
                f"error: {artifact} is a .pkg, which needs an uninstall stanza; "
                "pass --pkg-id <identifier>.\n"
                "       Find it without installing:\n"
                f"         pkgutil --expand-full {artifact} /tmp/pkg && \\\n"
                "           /usr/libexec/PlistBuddy -c 'Print :pkg-info:identifier' "
                "/tmp/pkg/*/PackageInfo\n"
                "       Or, on a machine that has it installed:  pkgutil --pkgs"
            )
        # stanza_artifact is already escaped and version-templated by the caller;
        # re-escaping would neutralise its #{version} marker.
        return ("\n".join([
            f'  pkg "{stanza_artifact}"',
            "",
            f'  uninstall pkgutil: "{_rb_str(pkg_id)}"',
        ]), f"verify the package id {pkg_id!r} matches the receipt in {artifact}")
    return (f'  app "{_rb_str(token)}.app"',
            f'the .app name inside {artifact} is a guess ("{token}.app") — verify it')


def render(token: str, repo: str, version: str, sha: str,
           url_template: str, desc: str, homepage: str, stanza: str,
           arch: str | None = None) -> str:
    """Render the Ruby cask source."""
    arch_lines = [f"  depends_on arch: :{arch}", ""] if arch else []
    return "\n".join([*[
        f'cask "{_rb_str(token)}" do',
        f'  version "{_rb_str(version)}"',
        f'  sha256 "{_rb_str(sha)}"',
        "",
        # Already escaped and templated by url_stanza_value(); re-escaping here
        # would neutralise the deliberate #{version} marker.
        f'  url "{url_template}"',
        f'  name "{_rb_str(repo)}"',
        f'  desc "{_rb_str(desc)}"',
        f'  homepage "{_rb_str(homepage)}"',
        "",
        "  livecheck do",
        "    url :url",
        "    strategy :github_latest",
        "  end",
        "",
        "  # This app is macOS-only. If `brew audit --online` reports the cask's",
        "  # macOS floor is higher than the bundle's LSMinimumSystemVersion, pin it",
        "  # explicitly to match, e.g. `depends_on macos: :big_sur`.",
        "  depends_on :macos",
        "",
    ], *arch_lines, *[
        stanza,
        "end",
        "",
    ]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", help="GitHub repo as 'owner/repo' or a github.com URL")
    parser.add_argument("--artifact",
                        help="release asset filename to package (default: first "
                             ".dmg/.pkg/.zip)")
    parser.add_argument("--name",
                        help="override the cask token (default: normalized repo name)")
    parser.add_argument("--pkg-id", metavar="ID",
                        help="package identifier for a .pkg asset's `uninstall "
                             "pkgutil:` stanza (required for .pkg; `brew audit "
                             "--cask --strict` rejects a pkg without one)")
    parser.add_argument("--seed", action="store_true",
                        help="write a placeholder cask (version/sha256 filled by the "
                             "first `brew bump-cask-pr`) without downloading anything")
    parser.add_argument("--tap-dir",
                        help="tap checkout to edit (default: HOMEBREW_TAP_DIR or the "
                             "current directory)")
    args = parser.parse_args()

    owner, repo = parse_repo(args.repo)
    token = normalize(args.name or repo)
    # `token` becomes a path segment below; an absolute-looking `--name` would make
    # pathlib's `/` discard the Casks/ prefix and write outside the tap.
    repo_root = tap_root(args.tap_dir)
    if "/" in token or "\\" in token:
        sys.exit(f"error: --name {args.name!r} must not contain path separators")
    # Same grammar update-cask-dispatch.yml validates its payload against. A token
    # outside it (`My App`, `@app`, `_`) survives normalize but yields a cask that
    # Homebrew cannot load and that the dispatch updater would refuse to bump, so
    # reject it here rather than writing the file.
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", token):
        sys.exit(f"error: cask token {token!r} (from {args.name or repo!r}) must "
                 "match ^[a-z0-9][a-z0-9-]*$; pass a valid --name")
    try:
        meta = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            sys.exit(f"error: repo {owner}/{repo} not found")
        raise
    desc = clean_desc(meta.get("description") or "TODO-set-description")
    homepage = meta.get("html_url") or f"https://github.com/{owner}/{repo}"

    if args.seed:
        # No release to introspect: assume this tap's common conventions (a `v<version>`
        # tag and a static artifact name) and template a URL the first bump can correct.
        artifact = args.artifact or f"{token}.dmg"
        if not artifact.lower().endswith(_ARTIFACT_PREFERENCE):
            sys.exit(f"error: {artifact!r} is not a supported cask asset "
                     f"({', '.join(_ARTIFACT_PREFERENCE)})")
        version, sha = _PLACEHOLDER_VERSION, _PLACEHOLDER_SHA
        stanza_artifact = _rb_str(artifact)
        url_template = (f"https://github.com/{_rb_str(owner)}/{_rb_str(repo)}"
                        f"/releases/download/v#{{version}}/{stanza_artifact}")
        print("==> Seeding placeholder cask. VERIFY these guessed URL conventions "
              "against the first real release (edit the cask if they differ):\n"
              f"      tag pattern: v#{{version}}   artifact: {artifact}\n"
              "    The first `brew bump-cask-pr` only refreshes version + sha256 from "
              "this URL; it can't fix a wrong tag/filename pattern.", file=sys.stderr)
    else:
        try:
            release = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                sys.exit(f"error: {owner}/{repo} has no published (non-draft, "
                         "non-prerelease) 'latest' release; use --seed to scaffold "
                         "a placeholder for the first release to fill in")
            raise
        tag = release["tag_name"]
        version = version_from_tag(tag)
        asset = select_asset(release.get("assets", []), args.artifact)
        artifact = asset["name"]
        sha = sha256_of(asset["browser_download_url"])
        # Rebuild the URL from the tag + filename, templated on the version so
        # `brew bump-cask-pr` (and livecheck) can bump it in place. Reuse the same
        # templated filename in the pkg stanza so it tracks the URL across bumps.
        # Escape before templatize (see _rb_str): the tag and asset name are
        # upstream-controlled, but the #{version} marker added here must stay live.
        stanza_artifact = templatize(_rb_str(artifact), version)
        # Template the URL the API gave us rather than rebuilding one from the raw
        # tag and filename. It is already percent-encoded, so an asset name with a
        # space or a `#` (or a tag containing `/`) stays byte-identical to the URL
        # the checksum above was computed from. A version is digits and dots, so it
        # is never encoded and templatize still finds it.
        # Template only what follows `/releases/download/` (tag and file name): a
        # repository name that happens to contain the version must stay literal.
        download_url = asset["browser_download_url"]
        head, sep, tail = download_url.partition("/releases/download/")
        url_template = _rb_str(head) + sep + templatize(_rb_str(tail), version) \
            if sep else templatize(_rb_str(download_url), version)

    stanza, hint = stanza_for(stanza_artifact, artifact, token, args.pkg_id)
    arch = arch_for(artifact)

    out = repo_root / "Casks" / f"{token}.rb"
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        sys.exit(f"error: {out} already exists; refusing to overwrite it")
    out.write_text(render(token, repo, version, sha, url_template, desc,
                          homepage, stanza, arch))
    print(f"==> Wrote {out.relative_to(repo_root)} (version {version})")
    if hint:
        print(f"warning: {hint}", file=sys.stderr)
    tap = resolve_tap(repo_root)
    ref = f"{tap}/{token}" if tap else f"<owner>/<tap>/{token}"
    print(f"\nNext: brew audit --cask --strict --online {ref}")


if __name__ == "__main__":
    main()
