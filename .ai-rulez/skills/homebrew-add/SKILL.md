---
type: Playbook
title: Homebrew Add
description: Use when adding a formula (PyPI Python CLI, or any other source build such as Rust, Go, Node, CMake or autotools) or a cask (prebuilt macOS app or per-platform CLI binary archives from a GitHub release) to this Homebrew tap, including a project that ships both. Triggers include "add <package> as a formula", "add <repo> as a cask" and any request to package something in the tap. Scaffold with the bundled scripts or `brew create --tap`; never hand-write resource blocks and never run brew create without --tap.
x-ai-rulez:
  kind: skill
  id: homebrew-add
  metadata:
    name: homebrew-add
---

# Add a Formula or Cask

Read the [template contract](../../references/contract.md) for the task names and paths
this skill relies on.

Two scaffolders bundled with this skill do the tedious, error-prone part
(dependency trees, sha256 values, livecheck blocks); you make the judgment calls
they cannot infer. Always scaffold with them: never hand-write resource blocks
and never run `brew create` without `--tap`, which writes into homebrew-core, the wrong
location. For a build system the scripts do not cover, use `brew create --tap` (see
"Other build systems").

Run them from the tap checkout, or pass `--tap-dir <path>` / set
`HOMEBREW_TAP_DIR`, as `python3 <skill-dir>/scripts/add_formula.py ...` and
`python3 <skill-dir>/scripts/add_cask.py ...`. They need only the standard library
and a `Formula/` or `Casks/` directory. The tap name used in printed audit
commands and by `--check` comes from the `origin` remote with its `homebrew-`
prefix removed (`owner/homebrew-tap` is `owner/tap`); override it with
`HOMEBREW_TAP=owner/tap` or `--tap owner/tap` when the remote is missing or wrong.

## Route by what upstream ships

Decide from one question: is the thing installed a Python package from PyPI, a
program built from a source release, or a prebuilt app or binary archive downloaded
from GitHub Releases?

| Upstream artifact | Kind | Script | Output |
| --- | --- | --- | --- |
| Python CLI on PyPI | formula | `add_formula.py <package>` | `Formula/<name>.rb` |
| Rust, Go, Node, CMake, autotools, Meson, Zig or similar source release | formula | `brew create --tap <owner>/<tap> --<kind> <url>` | `Formula/<name>.rb` |
| Per-platform binary archives (`.tar.gz`, `.zip`) of a CLI | cask, shaped by hand | none: see "Per-platform binary archives" | `Casks/<name>.rb` |
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

## Other build systems

Homebrew already has a template for each of these, so no scaffolder here duplicates
it: `--rust`, `--go`, `--node`, `--cmake`, `--autotools`, `--meson`, `--zig`,
`--ruby`, `--perl`, `--crystal` and `--cabal` (`brew create --help` lists the current
set).

```sh
HOMEBREW_EDITOR=true brew create --tap <owner>/<tap> --go \
  https://github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz
HOMEBREW_EDITOR=true brew create --tap <owner>/<tap> --node --set-name <name> \
  https://registry.npmjs.org/<package>/-/<package>-<version>.tgz
```

`--tap` is mandatory: without it the file lands in homebrew-core. The tap must be
tapped (`brew tap <owner>/<tap>`; if Homebrew refuses an untrusted tap, trust it with
`brew trust`). The file is written under `$(brew --repository <owner>/<tap>)/Formula`;
copy it into the checkout when that is not the checkout itself.
`HOMEBREW_EDITOR=true` stops it opening an editor. Use a tag archive URL: for a
GitHub URL `brew create` also reads the description, homepage and license from the
API; for any other URL it leaves them empty. It downloads the URL for the checksum.

The output is a skeleton, not a finished formula. Always:

- Delete the generated "PLEASE REMOVE ALL GENERATED COMMENTS" header.
- Set `desc` (capitalized, no trailing period, under 80 characters, not starting
  with "A" or "An"), `homepage` and an SPDX `license`.
- Replace `system "false"` in `test do` with a real check, such as
  `assert_match version.to_s, shell_output("#{bin}/<name> --version")`.
- Add a `livecheck` block: `url :stable` with `strategy :github_latest` for a GitHub
  release or tag archive; confirm with `brew livecheck <tap>/<name>`. The tap's
  update workflows find new versions through it.
- Go and Rust: remove the generated `deny_network_access!` and `fetch` method if
  present; `std_go_args` and `std_cargo_args` build without them.
- Rust: in a workspace the template builds the repo root; pass `path:` to
  `std_cargo_args` for the member crate, and check the crate really has a binary and
  is not feature-gated (`required-features`), since `cargo install` skips one.
- Add `depends_on` for libraries and tools the build needs, and pass any
  `./configure` or `cmake` options the project requires.
- Keep exactly one top-level `url` and `sha256`. The update workflows bump with
  `brew bump-formula-pr`, which edits only that pair: a formula with per-platform
  `url` stanzas inside `on_macos`/`on_arm` blocks fails with `Could not find 'url'
  stanza!` and is skipped, so it never updates.

Then run `brew audit --strict --online <tap>/<name>`, `brew install
--build-from-source <tap>/<name>` and `brew test <tap>/<name>`, and continue with
"After scaffolding".

## Per-platform binary archives

No scaffolder covers a CLI that ships one archive per OS and architecture, and a
formula is the wrong shape for it. Do not hand-write a formula with `url` and
`sha256` inside `on_macos`/`on_arm` blocks: `brew bump-formula-pr` edits only a
top-level `url`, fails with `Could not find 'url' stanza!` (checked against
Homebrew 7.0.11), and the update workflow then skips the formula with a warning,
so it never updates. Homebrew has no support for per-platform formula bumps and no
open plan for one.

Prefer one of these, in this order:

1. **Build from source** when the project is a Rust, Go, Node or C/C++ program:
   `brew create --tap` (above). One URL, bumped by the existing workflow.
2. **A cask shaped for `brew bump-cask-pr`:** one `url` template using `#{arch}`
   (and `#{os}` if Linux archives exist), `binary "<name>"` for the executable, and
   `sha256 arm: "...", intel: "..."` (Homebrew also reads `arm64_linux:` and
   `x86_64_linux:` keys). Keep the stanzas flat, not nested in `on_macos`/`on_arm`
   blocks, which `bump-cask-pr` leaves unchanged, and give it a real `livecheck`
   block (`url :url`, `strategy :github_latest`): `bump-cask-pr` refuses a cask whose
   livecheck is `skip`. Start from `add_cask.py` output or `brew create --cask --tap`
   and reshape it. Bumping with the `arm:`/`intel:` hash pair is covered by
   Homebrew's own specs; Linux hash keys and installing casks on Linux are not
   verified, so test on Linux before claiming support.
3. **The producer publishes it.** cargo-dist's Homebrew installer regenerates and
   pushes `Formula/<name>.rb` to the tap on every release (needs a
   `HOMEBREW_TAP_TOKEN` secret), and GoReleaser's `homebrew_casks` pushes a cask
   (`brews` is deprecated). Both write directly to the tap, so the tap's own bump
   workflows do not maintain those files, and GoReleaser's nested `on_arm` layout
   and `livecheck skip` stop `bump-cask-pr` from touching it. Choose this only when
   the project already builds with that tool.

Say which route you took and why, and that none of the three has a scaffolder here.

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
