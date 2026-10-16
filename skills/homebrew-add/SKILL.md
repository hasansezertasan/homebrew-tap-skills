---
description: Use when adding a formula (PyPI Python CLI) or a cask (prebuilt macOS app from a GitHub release) to this Homebrew tap, including a project that ships both. Triggers include "add <package> as a formula", "add <repo> as a cask" and any request to package something in the tap. Always scaffold with the bundled scripts; never hand-write resource blocks and never use brew create.
name: homebrew-add
---

# Add a Formula or Cask

Read the [template contract](references/contract.md) for the task names and paths
this skill relies on.

Two scaffolders bundled with this skill do the tedious, error-prone part
(dependency trees, sha256 values, livecheck blocks); you make the judgment calls
they cannot infer. Always scaffold with them: never hand-write resource blocks
and never run `brew create`, which writes into homebrew-core, the wrong location.

Run them from the tap checkout, or pass `--tap-dir <path>` / set
`HOMEBREW_TAP_DIR`, as `python3 <skill-dir>/scripts/add_formula.py ...` and
`python3 <skill-dir>/scripts/add_cask.py ...`. They need only the standard library
and a `Formula/` or `Casks/` directory. The tap name used in printed audit
commands and by `--check` comes from the `origin` remote with its `homebrew-`
prefix removed (`owner/homebrew-tap` is `owner/tap`); override it with
`HOMEBREW_TAP=owner/tap` or `--tap owner/tap` when the remote is missing or wrong.

## Route by what upstream ships

Decide from one question: is the thing installed a Python package from PyPI, or a
prebuilt app bundle downloaded from GitHub Releases?

| Upstream artifact | Kind | Script | Output |
| --- | --- | --- | --- |
| Python CLI on PyPI | formula | `add_formula.py <package>` | `Formula/<name>.rb` |
| Prebuilt macOS `.dmg`, `.pkg` or `.zip` on GitHub Releases | cask | `add_cask.py <owner>/<repo>` | `Casks/<name>.rb` |
| Both a Python CLI and a prebuilt app | both | both scripts | both files |

Follow the user if they say "as a formula" or "as a cask". If upstream ships both
and they do not say, make both (see "Ships both").

## Formula

```sh
python3 <skill-dir>/scripts/add_formula.py <package>
python3 <skill-dir>/scripts/add_formula.py <package> --extras tui --check
python3 <skill-dir>/scripts/add_formula.py <package> --test-command '#{bin}/<package> version'
```

The scaffolder reads PyPI metadata, selects a compatible Homebrew Python,
resolves the dependency tree, pins source distributions and checksums, adds a
`:pypi` livecheck and writes `Formula/<name>.rb`. The selected `python@3.x` must
be installed (`brew install python@3.13`): pip evaluates markers for the
interpreter it runs under, so resolving with another produces a resource tree
that silently does not match the formula. A package or dependency that publishes
neither an sdist nor a pure-Python wheel is refused rather than pinned to a
platform wheel. `--check` runs `brew audit --strict --online`, builds from source
and runs `brew test`; it needs the tap installed under Homebrew's `Library/Taps`
(`brew tap <owner>/<tap> <path>`), and is slow.

Then verify what the scaffolder cannot infer:

- **System (non-Python) libraries:** add `depends_on` by hand (PyYAML needs
  `libyaml`). Build toolchains such as Rust for `pydantic-core` are added
  automatically.
- **`license "TODO-set-SPDX-license"`:** PyPI gave a non-SPDX value (`MIT License`,
  `UNKNOWN`). Set the real SPDX identifier; `brew audit --strict` rejects the marker.
- **`--extras`:** it is recorded as a `# homebrew-tap:extras=` comment that both
  update workflows read. Keep it: without it the first version bump drops
  extras-only resources.
- **Test command:** the generated `test do` assumes `<name> --version`. PyPI does
  not expose console scripts, so that is a guess. Check the real CLI and pass
  `--test-command '#{bin}/<name> version'` when it differs. A package that ships no
  executable needs the assertion replaced with a real smoke test.
- **Python version:** override with `--python python@3.13` only when a dependency
  lacks support for the default. The scaffolder already uses a newer series when
  the package's `requires_python` floor demands it.
- **Names starting with a digit** (`2to3`) cannot be scaffolded: the Ruby class
  name would be invalid. Write that formula by hand with an explicit class name,
  and say so.

## Cask

```sh
GITHUB_TOKEN="$(gh auth token)" python3 <skill-dir>/scripts/add_cask.py <owner>/<repo>
python3 <skill-dir>/scripts/add_cask.py <owner>/<repo> --artifact App-arm64.dmg
python3 <skill-dir>/scripts/add_cask.py <owner>/<repo> --artifact App.pkg --pkg-id com.example.app
python3 <skill-dir>/scripts/add_cask.py <owner>/<repo> --seed
```

The scaffolder reads the latest release, selects a `.dmg`, `.pkg` or `.zip`
(`--artifact` when several exist), downloads it to compute the checksum, and
writes a version-templated URL with a `github_latest` livecheck. The URL is the
one GitHub's API reported, percent-encoded as returned. `--seed` writes a
placeholder cask (version `0.0.0`, zero checksum) the first `brew bump-cask-pr`
fills; use it before the producer's first release. Then verify:

- **`app "<name>.app"`:** the bundle name inside a `.dmg` or `.zip` is a guess;
  check the real one.
- **`.pkg` assets need `--pkg-id`:** a `pkg` stanza without `uninstall pkgutil:` is
  rejected by `brew audit --cask --strict`. The scaffolder refuses to guess and
  prints how to read the identifier from the asset.
- **`depends_on macos:`:** if the online audit says the cask's floor is higher than
  the bundle's `LSMinimumSystemVersion`, pin it (`depends_on macos: :big_sur`).
- **`depends_on arch:`:** added when the asset name marks one architecture; check
  it against what upstream ships (a universal build gets none).
- **`caveats`:** add them when the app needs permissions or Gatekeeper approval.
- **Seeded casks:** they are not installable. Keep them out of any claim that the
  cask works until a real release exists, the first bump has run and the cask has
  been audited.

## Ships both

A Python CLI and a prebuilt app of the same name give `Formula/<name>.rb` and
`Casks/<name>.rb`. Plain `brew install <name>` is then ambiguous; add a note to
the tap README distinguishing `brew install --formula` from `--cask`.

## After scaffolding

1. Review the generated description (capitalized, no trailing period), license,
   URLs, test command, bundle names and dependencies.
2. Run `mise run generate-readme` in the tap and commit the regenerated package
   table with the Ruby file; CI fails a stale table.
3. Invoke `homebrew-verify` for the pre-PR gate: audit, install and test
   evidence, catalog freshness and local checks. If skills are not
   auto-discovered, read its sibling `SKILL.md`.

Follow the tap's own `AGENTS.md`, `CONTRIBUTING.md` and PR template for branch
names, commit titles and review flow, and include the verification evidence in
the PR body. Pushing and opening the PR follow the user's approval rules.
