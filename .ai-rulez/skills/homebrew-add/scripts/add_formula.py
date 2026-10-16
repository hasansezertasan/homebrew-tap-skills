#!/usr/bin/env python3
"""Scaffold a complete Homebrew formula for a PyPI package.

Resolves the full dependency tree (including chosen extras) via a ``pip --dry-run``
report, maps every dependency back to its PyPI source distribution (sdist) with a
sha256, and writes ``Formula/<name>.rb`` following this tap's conventions. Run it from the tap
checkout, or pass ``--tap-dir`` / set ``HOMEBREW_TAP_DIR``.

Standard library only — no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from tap_name import resolve as resolve_tap
from tap_name import tap_root

PYPI = "https://pypi.org/pypi"

# Tap convention: package against the current default interpreter unless the
# target package's requires_python floor is newer.
DEFAULT_PYTHON_SERIES = "3.14"

# Packages whose presence in the resolved tree implies a build-time toolchain.
_BUILD_DEPS_BY_RESOURCE = {
    "pydantic-core": '"rust" => :build',
}

# Minimal SPDX mapping for the common "License :: OSI Approved :: ..." classifiers.
_LICENSE_BY_CLASSIFIER = {
    "MIT License": "MIT",
    "MIT No Attribution License (MIT-0)": "MIT-0",
    "ISC License (ISCL)": "ISC",
    "Apache Software License": "Apache-2.0",
    "BSD License": "BSD-3-Clause",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}


def fetch_json(url: str) -> dict:
    """Fetch and decode a JSON document, failing loudly on HTTP errors."""
    with urllib.request.urlopen(url) as response:  # noqa: S310 - trusted PyPI host
        return json.load(response)


def pypi_release(name: str, version: str | None = None) -> dict:
    """Return the PyPI JSON payload for a package (latest release unless pinned)."""
    suffix = f"/{version}" if version else ""
    return fetch_json(f"{PYPI}/{name}{suffix}/json")


def normalize(name: str) -> str:
    """Normalize a project name to its PEP 503 form (Homebrew resource naming)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def class_name(name: str) -> str:
    """Derive a Ruby class name from a package name (e.g. ``markdown-it-py``).

    Raises ``ValueError`` for a name that cannot produce a valid Ruby constant.
    PyPI allows a leading digit, but ``class 2to3 < Formula`` is a Ruby syntax
    error, so emitting it would write a file that cannot even be parsed. Homebrew's
    own ``Formulary.class_s`` has the same gap (``brew create 2to3`` generates the
    same broken class), so there is no upstream convention to follow — fail loudly
    instead of writing a broken formula.
    """
    derived = "".join(part.capitalize() for part in re.split(r"[-_.]+", name))
    if not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", derived):
        raise ValueError(
            f"cannot derive a valid Ruby class name from {name!r} (got "
            f"{derived!r}); Homebrew formula classes must start with a letter. "
            "Write this formula by hand with an explicit class name."
        )
    return derived


# SPDX identifiers this scaffolder recognises: the values of the classifier map
# above plus the other identifiers common on PyPI. Deliberately small — Homebrew
# validates the full SPDX list at audit time, and the point here is only to keep
# a legacy free-text value like "MIT License" or "UNKNOWN" from being emitted as
# if it were an identifier.
_SPDX_IDS = frozenset(_LICENSE_BY_CLASSIFIER.values()) | {
    "0BSD", "AGPL-3.0-only", "AGPL-3.0-or-later", "Apache-2.0", "BSD-2-Clause",
    "BSD-3-Clause", "BSL-1.0", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0",
    "EPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only",
    "GPL-3.0-or-later", "ISC", "LGPL-2.1-only", "LGPL-3.0-only",
    "LGPL-3.0-or-later", "MIT", "MIT-0", "MPL-2.0", "PSF-2.0", "Python-2.0",
    "Unlicense", "Zlib",
}
_SPDX_OPERATORS = frozenset({"AND", "OR", "WITH"})


def is_spdx_expression(value: str) -> bool:
    """Whether a raw license string parses as an SPDX expression we recognise.

    PyPI's free-text ``license`` field is where projects put things like
    ``MIT License``, ``BSD License``, or ``UNKNOWN``. None of those are SPDX
    identifiers, so emitting them verbatim produces a formula that fails
    ``brew audit --strict`` with no hint that the field needs fixing. Accept a
    recognised identifier, optionally joined by SPDX operators (``MIT OR
    Apache-2.0``) and optionally suffixed with ``+``, and reject anything else so
    the caller falls back to the explicit TODO marker.
    """
    tokens = value.replace("(", " ").replace(")", " ").split()
    if not tokens:
        return False
    for index, token in enumerate(tokens):
        # Operators sit between identifiers, never at either end.
        if index % 2:
            if token.upper() not in _SPDX_OPERATORS:
                return False
        elif index and tokens[index - 1].upper() == "WITH":
            # `WITH` takes a license *exception* id (`Apache-2.0 WITH
            # LLVM-exception`), which is a separate SPDX list. Accept anything
            # identifier-shaped and let `brew audit` validate the exact name.
            if not re.fullmatch(r"[A-Za-z0-9.+-]+", token):
                return False
        elif token.rstrip("+") not in _SPDX_IDS:
            return False
    return len(tokens) % 2 == 1


def spdx_license(info: dict) -> str:
    """Best-effort SPDX license, preferring the PEP 639 expression field."""
    expression = (info.get("license_expression") or "").strip()
    if expression:
        return expression
    for classifier in info.get("classifiers", []):
        prefix = "License :: OSI Approved :: "
        if classifier.startswith(prefix):
            label = classifier[len(prefix):]
            if label in _LICENSE_BY_CLASSIFIER:
                return _LICENSE_BY_CLASSIFIER[label]
    raw = (info.get("license") or "").strip()
    if raw and len(raw) <= 40 and "\n" not in raw and is_spdx_expression(raw):
        return raw
    if raw:
        print(f"warning: license {raw!r} is not an SPDX expression; leaving the "
              "TODO marker for you to fill in", file=sys.stderr)
    return "TODO-set-SPDX-license"


def clean_desc(summary: str) -> str:
    """Format a PyPI summary as a Homebrew ``desc``.

    ``brew audit --strict`` rejects a leading article and requires a capital first
    letter (both in ``rubocops/shared/desc_helper.rb``), so strip the article and a
    trailing period, then capitalize. The article match is case-insensitive because
    the audit's own regex is. Mirrors the helper in ``add_cask.py``.
    """
    desc = re.sub(r"^(?:an?|the)\s+", "", summary.strip().rstrip("."),
                  flags=re.IGNORECASE)
    return desc[:1].upper() + desc[1:] if desc else desc


def min_python(requires_python: str | None) -> str | None:
    """Extract the minimum ``3.x`` series from a ``requires_python`` spec.

    Covers the lower-bound operators that appear in practice: ``>``/``>=`` plus the
    exact (``==3.12``, ``==3.12.*``) and compatible-release (``~=3.12``) forms,
    which pin a floor just as firmly. This is a pragmatic scan, not a PEP 440
    solver — these scripts are stdlib-only, so ``packaging`` is not available.
    ``!=`` exclusions are deliberately ignored: they carve holes out of a range
    rather than setting a floor.
    """
    if not requires_python:
        return None
    matches = re.findall(r"(?:>=?|==|~=)\s*3\.(\d+)", requires_python)
    if not matches:
        return None
    return f"3.{min(int(m) for m in matches)}"


def max_python(requires_python: str | None) -> str | None:
    """Highest ``3.x`` series allowed by an upper bound, or None if unbounded.

    Returns the newest ``3.x`` that still satisfies a ``<`` / ``<=`` clause:
    ``<3.14`` -> ``3.13``, ``<=3.12`` -> ``3.12``. Major-version caps like
    ``<4`` don't restrict any ``3.x`` and are ignored.
    """
    if not requires_python:
        return None
    cap: int | None = None
    for op, minor in re.findall(r"(<=?)\s*3\.(\d+)", requires_python):
        allowed = int(minor) if op == "<=" else int(minor) - 1
        cap = allowed if cap is None else min(cap, allowed)
    # An exact pin caps as hard as a `<` clause: `==3.12` and `==3.12.*` both
    # exclude 3.13. So does a compatible release pinned past the minor
    # (`~=3.12.1` means `>=3.12.1, ==3.12.*`), while a bare `~=3.12` allows any
    # later 3.x and must not cap.
    for minor in re.findall(r"==\s*3\.(\d+)", requires_python):
        cap = int(minor) if cap is None else min(cap, int(minor))
    for minor in re.findall(r"~=\s*3\.(\d+)\.\d", requires_python):
        cap = int(minor) if cap is None else min(cap, int(minor))
    return f"3.{cap}" if cap is not None else None


def _series_tuple(series: str) -> tuple[int, ...]:
    """Parse a ``3.x`` series into a comparable integer tuple."""
    return tuple(int(part) for part in series.split("."))


def brew_python(series: str) -> tuple[str, str]:
    """Return the ``python@3.x`` formula name and its interpreter path.

    Exits when the formula is not installed rather than falling back to the
    interpreter running this script. pip evaluates environment markers and picks
    compatible releases for *the interpreter it runs under*, so resolving a
    3.14-targeted formula from 3.12 silently produces the wrong resource tree —
    the generated formula would declare ``python@3.14`` and pin dependencies
    resolved for 3.12. That is worse than not scaffolding at all, because the
    mismatch is invisible in the output.
    """
    formula = f"python@{series}"
    try:
        prefix = subprocess.run(
            ["brew", "--prefix", formula],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        interpreter = Path(prefix) / "libexec" / "bin" / "python"
        if interpreter.exists():
            return formula, str(interpreter)
        detail = f"{formula} is known to brew but {interpreter} is missing"
    except subprocess.CalledProcessError:
        detail = f"brew does not know {formula}"
    except FileNotFoundError:
        detail = "brew is not installed"
    sys.exit(f"error: cannot resolve dependencies for {formula} ({detail}).\n"
             f"       Install it first:  brew install {formula}\n"
             "       Resolution must run under the same interpreter the formula "
             "declares, or the pinned resource tree will not match it.")


def resolve_tree(interpreter: str, requirement: str) -> list[tuple[str, str]]:
    """Resolve a requirement to a flat list of ``(name, version)`` dependencies."""
    result = subprocess.run(
        [interpreter, "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "--dry-run", "--ignore-installed",
         "--report", "-", requirement],
        capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)
    return [
        (item["metadata"]["name"], item["metadata"]["version"])
        for item in report["install"]
    ]


def _is_pure_python_wheel(filename: str) -> bool:
    """Whether a wheel filename's compatibility tags make it platform-independent.

    PEP 427 names a wheel ``{dist}-{version}(-{build})?-{python}-{abi}-{platform}``
    so the last tag group is the platform; ``any`` with a ``none`` ABI is the
    portable case (``py3-none-any``, ``py2.py3-none-any``).
    """
    parts = filename.removesuffix(".whl").split("-")
    if len(parts) < 3:
        return False
    python_tag, abi_tag, platform_tag = parts[-3:]
    return (platform_tag == "any" and abi_tag == "none"
            and all(tag.startswith("py") for tag in python_tag.split(".")))


def sdist_for(name: str, version: str) -> tuple[str, str, bool]:
    """Return ``(url, sha256, is_sdist)`` for a package version, preferring the sdist."""
    payload = pypi_release(name, version)
    for entry in payload["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"], entry["digests"]["sha256"], True
    # Wheel-only release. Only a pure-Python wheel is safe to pin: a platform
    # wheel (manylinux, macOS-arm64, win_amd64) or one built for a single CPython
    # ABI is tied to an interpreter and architecture the formula does not
    # necessarily target, so pinning it produces a formula that fails to install
    # or to bottle on the other architecture. Taking urls[0] picked whichever file
    # PyPI happened to list first.
    for entry in payload["urls"]:
        if entry["packagetype"] == "bdist_wheel" and _is_pure_python_wheel(
                entry["filename"]):
            print(f"warning: {name} {version} has no sdist; using the pure-Python "
                  f"wheel {entry['filename']}", file=sys.stderr)
            return entry["url"], entry["digests"]["sha256"], False
    available = ", ".join(e["filename"] for e in payload["urls"]) or "none"
    sys.exit(f"error: {name} {version} publishes no sdist and no pure-Python "
             f"wheel, so there is no artifact that builds for every target.\n"
             f"       Files on PyPI: {available}\n"
             "       Pin a different version, or write this resource by hand with "
             "the platform wheel you want.")


def _rb_str(value: str) -> str:
    """Escape a value for a double-quoted Ruby string literal in the generated formula.

    Formula files are Ruby, evaluated by ``brew audit``/``install``. PyPI metadata is
    upstream-controlled for an arbitrary package, so an unescaped quote or backslash
    would break out of the literal, and ``#{...}`` would interpolate — running
    arbitrary Ruby the moment the formula is loaded. Mirrors ``_rb_str`` in
    ``add_cask.py``.
    """
    return (value.replace("\\", "\\\\")
                 .replace('"', '\\"')
                 .replace("#{", "\\#{"))


def default_test_command(name: str) -> str:
    """Best-guess smoke test for a CLI whose console script cannot be introspected.

    PyPI's JSON API does not expose ``console_scripts``, so the executable name and
    its version flag are a guess: many CLIs use a bare ``version`` subcommand, and a
    library with no console script has no executable at all. Override with
    ``--test-command``; both README and the ``homebrew-add`` skill call this out as a
    required human check before committing.
    """
    return f"#{{bin}}/{name} --version"


# Marker the update workflows grep for to recover a formula's extras. Homebrew
# infers the package name for `brew update-python-resources` from the formula's
# stable URL, which carries no extras, so a bump would otherwise re-resolve the
# base requirement only and drop every resource that exists solely for an extra.
EXTRAS_MARKER = "# homebrew-tap:extras="


def render(name: str, info: dict, sdist_url: str, sdist_sha: str,
           python_formula: str, resources: list[tuple[str, str, str]],
           build_deps: list[str], test_command: str | None = None,
           extras: str = "") -> str:
    """Render the Ruby formula source."""
    test_command = test_command or default_test_command(name)
    # Escape for the double-quoted Ruby literal; `#{bin}` interpolation stays live.
    test_command = test_command.replace("\\", "\\\\").replace('"', '\\"')
    homepage = (info.get("project_urls") or {}).get("Homepage") \
        or info.get("home_page") or f"https://pypi.org/project/{name}/"
    lines = [
        f"class {class_name(name)} < Formula",
        "  include Language::Python::Virtualenv",
        "",
    ]
    if extras:
        lines += [
            f"  {EXTRAS_MARKER}{extras}",
            "  # ^ read by update-formulas.yml / update-formula-dispatch.yml, which",
            "  #   pass it to `brew update-python-resources --package-name` so a",
            "  #   version bump keeps the resources these extras pull in.",
            "",
        ]
    lines += [
        f'  desc "{_rb_str(clean_desc(info["summary"] or ""))}"',
        f'  homepage "{_rb_str(homepage)}"',
        f'  url "{_rb_str(sdist_url)}"',
        f'  sha256 "{_rb_str(sdist_sha)}"',
        f'  license "{_rb_str(spdx_license(info))}"',
        "",
        "  livecheck do",
        "    url :stable",
        "    strategy :pypi",
        "  end",
        "",
    ]
    # Build dependencies must precede runtime deps (Homebrew audit ordering).
    for dep in build_deps:
        lines.append(f"  depends_on {dep}")
    lines += [
        f'  depends_on "{python_formula}"',
        "",
    ]
    for res_name, url, sha in resources:
        lines += [
            f'  resource "{_rb_str(res_name)}" do',
            f'    url "{_rb_str(url)}"',
            f'    sha256 "{_rb_str(sha)}"',
            "  end",
            "",
        ]
    lines += [
        "  def install",
        "    virtualenv_install_with_resources",
        "  end",
        "",
        "  test do",
        f'    assert_match version.to_s, shell_output("{test_command}")',
        "  end",
        "end",
        "",
    ]
    return "\n".join(lines)


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
    # A contributor working directly inside Homebrew's Library/Taps checkout is
    # already editing the file brew reads: staging it would be shutil.copy onto
    # itself (SameFileError), and the cleanup below would delete their work.
    staged = source.resolve() != tap_formula.resolve()
    if staged:
        shutil.copy(source, tap_formula)
    else:
        print(f"==> {source} is already the active tap's copy; auditing in place")
    ref = f"{tap}/{name}"
    try:
        for cmd in (
            ["brew", "audit", "--strict", "--online", ref],
            ["brew", "install", "--build-from-source", ref],
            ["brew", "test", ref],
        ):
            print(f"\n==> {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
    finally:
        if staged:
            tap_formula.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", help="PyPI package name")
    parser.add_argument("--extras", default="",
                        help="comma-separated extras to include (e.g. 'tui')")
    parser.add_argument("--version", help="package version (default: latest on PyPI)")
    parser.add_argument("--python", metavar="python@3.X",
                        help="override python formula (e.g. 'python@3.13')")
    parser.add_argument("--test-command", metavar="CMD",
                        help="smoke test command for `test do` (default: "
                             "'#{bin}/<name> --version'); use when the CLI's version "
                             "flag differs or the package ships no console script")
    parser.add_argument("--check", action="store_true",
                        help="audit, build-from-source, and test the result")
    parser.add_argument("--tap", help="tap name used by --check (default: infer from origin)")
    parser.add_argument("--tap-dir",
                        help="tap checkout to edit (default: HOMEBREW_TAP_DIR or the "
                             "current directory)")
    args = parser.parse_args()

    release = pypi_release(args.package, args.version)
    info = release["info"]
    name = normalize(info["name"])
    version = info["version"]
    try:
        class_name(name)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    sdist_url, sdist_sha, is_sdist = sdist_for(info["name"], version)
    if not is_sdist:
        # virtualenv_install_with_resources builds the stable archive from source.
        sys.exit(f"error: {name} {version} publishes no sdist, so the formula's "
                 "stable archive cannot be built from source; write it by hand.")

    if args.python:
        # `--python python` would otherwise raise IndexError on the split below.
        if not re.fullmatch(r"python@3\.\d+", args.python):
            parser.error(f"--python must look like 'python@3.13', got {args.python!r}")
        series = args.python.split("@", 1)[1]
    else:
        # Default to the tap's current interpreter, but honor a package whose
        # requires_python floor is newer than the default, or whose upper bound
        # excludes the default (e.g. ">=3.10,<3.14" can't use python@3.14).
        requires_python = info.get("requires_python")
        series = DEFAULT_PYTHON_SERIES
        floor = min_python(requires_python)
        cap = max_python(requires_python)
        if floor and _series_tuple(floor) > _series_tuple(DEFAULT_PYTHON_SERIES):
            print(f"warning: {name} requires Python >= {floor}; using python@"
                  f"{floor} instead of the default python@{DEFAULT_PYTHON_SERIES}",
                  file=sys.stderr)
            series = floor
        elif cap and _series_tuple(cap) < _series_tuple(DEFAULT_PYTHON_SERIES):
            print(f"warning: {name} ({requires_python}) excludes python@"
                  f"{DEFAULT_PYTHON_SERIES}; using python@{cap} instead",
                  file=sys.stderr)
            series = cap
    python_formula, interpreter = brew_python(series)

    requirement = f"{args.package}=={version}"
    if args.extras:
        requirement = f"{args.package}[{args.extras}]=={version}"
    print(f"==> Resolving {requirement} with {interpreter}")

    resources: list[tuple[str, str, str]] = []
    for dep_name, dep_version in resolve_tree(interpreter, requirement):
        if normalize(dep_name) == name:
            continue
        url, sha, _ = sdist_for(dep_name, dep_version)
        resources.append((normalize(dep_name), url, sha))
    resources.sort(key=lambda r: r[0])

    # Emit unique build-time deps implied by the resolved tree (e.g. rust for
    # pydantic-core). De-duplicate so two resources that
    # map to the same toolchain don't render duplicate `depends_on` lines.
    build_deps = sorted(
        {
            _BUILD_DEPS_BY_RESOURCE[res_name]
            for res_name, _, _ in resources
            if res_name in _BUILD_DEPS_BY_RESOURCE
        }
    )

    repo = tap_root(args.tap_dir)
    out = repo / "Formula" / f"{name}.rb"
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        sys.exit(f"error: {out} already exists; refusing to overwrite it")
    out.write_text(
        render(name, info, sdist_url, sdist_sha, python_formula, resources,
               build_deps, args.test_command, args.extras))
    print(f"==> Wrote {out.relative_to(repo)} "
          f"({len(resources)} resources, {python_formula})")

    tap = args.tap or resolve_tap(repo)
    if args.check:
        if not tap:
            sys.exit("error: cannot infer the tap name; pass --tap owner/tap or set "
                     "HOMEBREW_TAP")
        run_checks(repo, name, tap)
    else:
        ref = f"{tap}/{name}" if tap else f"<owner>/<tap>/{name}"
        print(f"\nNext: brew audit --strict --online {ref}  "
              "(or re-run with --check)")


if __name__ == "__main__":
    main()
