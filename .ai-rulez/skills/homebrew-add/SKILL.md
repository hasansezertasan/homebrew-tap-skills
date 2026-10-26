---
type: Playbook
title: Homebrew Add
description: Use when adding a formula (PyPI Python CLI, or a source build such as Rust, Go, Node, CMake or autotools) or a cask (prebuilt macOS app or per-platform CLI binary archives from a GitHub release) to this Homebrew tap, including a project that ships both. Triggers include "add <package> as a formula", "add <repo> as a cask" and any request to package something in the tap. Start from `brew create --tap` and finish the skeleton by hand; never hand-write resource blocks and never run brew create without --tap.
x-ai-rulez:
  kind: skill
  id: homebrew-add
  metadata:
    name: homebrew-add
---

# Add a Formula or Cask

Read the [template contract](../../references/contract.md) for the task names and paths
this skill relies on.

Homebrew generates the file; you finish it. `brew create` downloads the artifact,
computes its checksum, fills in what GitHub can tell it and, for Python, resolves the
whole resource tree. It leaves a skeleton, so the work here is choosing the route and
completing what the skeleton omits. This skill bundles no scripts: lean on Homebrew's
own commands, and read `brew create --help` and the Formula and Cask Cookbooks when
something here is out of date.

## Route by what upstream ships

Decide from one question: is the thing installed a Python package from PyPI, a
program built from a source release, or a prebuilt app or binary archive downloaded
from GitHub Releases?

| Upstream artifact | Kind | Start with |
| --- | --- | --- |
| Python CLI on PyPI | formula | `brew create --tap <owner>/<tap> --python <sdist url>` |
| Rust, Go, Node, CMake, autotools, Meson, Zig or similar source release | formula | `brew create --tap <owner>/<tap> --<kind> <url>` |
| Prebuilt macOS `.dmg`, `.pkg` or `.zip` on GitHub Releases | cask | `brew create --cask --tap <owner>/<tap> --set-name <token> <asset url>` |
| Per-platform binary archives (`.tar.gz`, `.zip`) of a CLI | cask, shaped by hand | see "Per-platform binary archives" |
| Both a Python CLI and a prebuilt app | both | both routes |

Follow the user if they say "as a formula" or "as a cask". If upstream ships both
and they do not say, make both (see "Ships both").

## Create the file

```sh
HOMEBREW_EDITOR=true brew create --tap <owner>/<tap> --<kind> [--set-name <name>] <url>
```

- **`--tap` is mandatory.** Without it the file lands in homebrew-core, the wrong
  location. `HOMEBREW_EDITOR=true` stops it opening an editor.
- **The tap must be tapped** (`brew tap <owner>/<tap> <path-to-checkout>`). If Homebrew
  refuses an untrusted tap, run `brew trust --tap <owner>/<tap>`. The file is written
  under `$(brew --repository <owner>/<tap>)`. Finish and validate it there: the audit,
  install and test commands resolve that installed copy, not your checkout. Then copy
  the finished file into the checkout when that is not the checkout itself. The tap name is the origin remote without its `homebrew-`
  prefix (`owner/homebrew-tap` is `owner/tap`).
- **Use the URL of a release artifact** (a tag archive, an sdist, an asset). For a
  GitHub URL `brew create` also reads the description, homepage and license from the
  API; for any other URL it leaves them empty.
- **The output is a skeleton.** Always remove the generated "PLEASE REMOVE ALL
  GENERATED COMMENTS" header, set `desc` (capitalized, no trailing period, under 80
  characters, not starting with "A" or "An") and `homepage`, and add a `livecheck`
  block chosen by how upstream publishes versions (see below). The tap's update
  workflows find new versions through livecheck. For a formula, also set an SPDX
  `license` (a non-SPDX value fails `brew audit --strict`) and replace the
  placeholder `system "false"` test with a real check. A cask has neither a
  `license` nor a `test` stanza: its fields are listed under "Cask".
- **Do not hand-write resource blocks.** Homebrew writes and refreshes them
  (`brew update-python-resources`).

Then validate. A formula: `brew audit --strict --online <tap>/<name>`, `brew install
--build-from-source <tap>/<name>` and `brew test <tap>/<name>`. A cask: `brew audit
--cask --strict --online <tap>/<token>`, then `brew install --cask <tap>/<token>` and
`brew uninstall --cask <tap>/<token>` (a cask has no source build and no `brew test`).
Continue with "After creating".

## Python formula

```sh
SDIST="$(curl -s https://pypi.org/pypi/<package>/json | python3 -c \
  'import json,sys;print([u["url"] for u in json.load(sys.stdin)["urls"] if u["packagetype"]=="sdist"][0])')"
HOMEBREW_EDITOR=true brew create --tap <owner>/<tap> --python --set-name <name> "$SDIST"
```

This resolves the whole dependency tree into `resource` blocks and writes
`virtualenv_install_with_resources`, against the current default `python@3.x`. PyPI
metadata is not read, so finish by hand:

- **`desc`, `homepage`, `license`:** take them from the PyPI page. A free-text PyPI
  license (`MIT License`, `UNKNOWN`) must become an SPDX identifier.
- **`livecheck`:** `url :stable` with `strategy :pypi`.
- **Test:** the template assumes nothing. A guess such as `<name> --version` needs
  checking against the real CLI (PyPI does not expose console scripts); a package
  that ships no executable needs a real smoke test, such as importing it.
- **Extras:** `brew update-python-resources --package-name='<package>[<extra>]'
  <tap>/<name>` re-resolves with them. Record them as a `# homebrew-tap:extras=<a,b>`
  comment in the formula; both update workflows read it, and without it the first
  version bump drops extras-only resources. Keep the comment verbatim.
- **Python version:** change `depends_on "python@3.x"` when the package's
  `requires_python` floor is newer than the default or an upper bound excludes it,
  then re-run `brew update-python-resources` so the tree matches. Resolution must run
  under the interpreter the formula declares, so install that `python@3.x` first.
- **Native dependencies:** add `depends_on` by hand for system libraries (PyYAML needs
  `libyaml`) and toolchains (`rust` for `pydantic-core`).
- **A dependency with only a platform wheel:** if a resource cannot be pinned to a
  source distribution, report the packaging blocker rather than pinning a wheel for
  one platform.
- **Names starting with a digit** (`2to3`) make an invalid Ruby class name. Write the
  class name by hand and say so.

## Other build systems

Homebrew has a template for each of these: `--rust`, `--go`, `--node`, `--cmake`,
`--autotools`, `--meson`, `--zig`, `--ruby`, `--perl`, `--crystal` and `--cabal`
(`brew create --help` lists the current set).

```sh
HOMEBREW_EDITOR=true brew create --tap <owner>/<tap> --go \
  https://github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz
HOMEBREW_EDITOR=true brew create --tap <owner>/<tap> --node --set-name <name> \
  https://registry.npmjs.org/<package>/-/<package>-<version>.tgz
```

Beyond "Create the file":

- **`livecheck`:** `url :stable` alone for a GitHub tag archive (Homebrew's Git
  strategy reads the tags), and `strategy :github_latest` only when the project
  publishes GitHub Releases and its tags are not a reliable stream (pre-release tags,
  tags without a release). `github_latest` on a tags-only repository finds nothing,
  and the update workflows treat that as "up to date", so new versions are never
  proposed. Confirm with `brew livecheck <tap>/<name>`: it must report a version.
- **Go and Rust:** keep the generated `fetch` method (`go mod download`,
  `cargo fetch`) and `deny_network_access!`. Homebrew runs `fetch` with network access
  and then runs `install` offline, so removing `fetch` alone leaves the build unable
  to download its modules or crates.
- **Rust:** in a workspace the template builds the repo root; pass `path:` to
  `std_cargo_args` for the member crate, and check the crate really has a binary and
  is not feature-gated (`required-features`), since `cargo install` skips one.
- **`depends_on` and build options:** add the libraries and tools the build needs, and
  any `./configure` or `cmake` options the project requires.
- **Keep exactly one top-level `url` and `sha256`** unless the tap's update workflows
  handle more (see "Per-platform binary archives"): `brew bump-formula-pr` edits only
  that pair.

## Per-platform binary archives

A CLI that ships one archive per OS and architecture does not fit a formula in the
tap's default update flow. Read the tap's update workflows
(`.github/workflows/update-formulas.yml` and `update-formula-dispatch.yml`) first.
The template's bump formulae with `brew bump-formula-pr`, which edits only a
top-level `url`: on a formula with `url` and `sha256` inside `on_macos`/`on_arm`
blocks it fails with `Could not find 'url' stanza!` (checked against Homebrew
7.0.11), and the workflow then skips the formula with a warning, so it never
updates. Homebrew has no support for per-platform formula bumps and no open plan for
one. If the tap's workflows have been changed to handle that shape, a formula is
fine; otherwise do not write one.

Prefer one of these, in this order:

1. **Build from source** when the project is a Rust, Go, Node or C/C++ program:
   "Other build systems". One URL, bumped by the existing workflow.
2. **A cask shaped for `brew bump-cask-pr`:** one `url` template using `#{arch}` (and
   `#{os}` if Linux archives exist), `binary "<name>"` for the executable, and
   `sha256 arm: "...", intel: "..."` (Homebrew also reads `arm64_linux:` and
   `x86_64_linux:` keys). The URL substitutions need their own stanzas, or the
   components come out empty: define `arch arm: "<arm string>", intel: "<intel
   string>"` with the strings the asset names use (`aarch64`/`x86_64`,
   `arm64`/`amd64`) and, for Linux, `os macos: "<string>", linux: "<string>"` (Cask
   Cookbook, "Handling different system configurations"). Keep the stanzas flat, not nested in `on_macos`/`on_arm`
   blocks, which `bump-cask-pr` leaves unchanged, and give it a real `livecheck`
   block: `bump-cask-pr` refuses a cask whose livecheck is `skip`. Choose the URL and
   strategy from how upstream publishes versions (`url :url` with `strategy
   :github_latest` when the project publishes suitable GitHub Releases; otherwise the
   tag or page strategy that `brew livecheck` confirms). Start from `brew create --cask --tap` and reshape it. Bumping
   with the `arm:`/`intel:` hash pair is covered by Homebrew's own specs; Linux hash
   keys and installing casks on Linux are not verified, so test on Linux before
   claiming support.
3. **The producer publishes it.** cargo-dist's Homebrew installer regenerates and
   pushes `Formula/<name>.rb` to the tap on every release (needs a
   `HOMEBREW_TAP_TOKEN` secret), and GoReleaser's `homebrew_casks` pushes a cask
   (`brews` is deprecated). Both write directly to the tap, so the tap's own bump
   workflows do not maintain those files, and GoReleaser's nested `on_arm` layout and
   `livecheck skip` stop `bump-cask-pr` from touching it. Choose this only when the
   project already builds with that tool.

Say which route you took and why.

## Cask

```sh
gh release view --repo <owner>/<repo> --json tagName,assets --jq '.assets[].browser_download_url'
HOMEBREW_EDITOR=true brew create --cask --tap <owner>/<tap> --set-name <token> <asset url>
```

The cask comes out with the version templated into the URL and the checksum filled.
It leaves the rest to you:

- **Token:** `--set-name` is required; the default comes from the file name. It must
  match `^[a-z0-9][a-z0-9-]*$`, the grammar the dispatch workflow validates, or the
  cask cannot be loaded or bumped.
- **`desc`, `homepage`, `name`:** from the repo; same `desc` rules as above.
- **`livecheck`:** replace the empty placeholder with a real, non-skipped block:
  `url :url` with `strategy :github_latest` when the project publishes suitable
  GitHub Releases, otherwise the tag or page strategy that `brew livecheck` confirms.
- **Version in the URL:** `version` is the number only (tag `v1.2.3` gives `1.2.3`),
  and the URL carries it as `#{version}` with any tag prefix kept literal
  (`/download/v#{version}/App-#{version}.dmg`). A URL with the version hard-coded
  will not bump. Keep the URL percent-encoded as the API reports it.
- **`app "<name>.app"`:** the bundle name inside a `.dmg` or `.zip` is a guess; check
  the real one.
- **`.pkg` assets:** a `pkg` stanza needs `uninstall pkgutil: "<id>"`, or
  `brew audit --cask --strict` rejects it. Read the id without installing:
  `pkgutil --expand-full <file>.pkg /tmp/pkg` and print `:pkg-info:identifier` from
  `/tmp/pkg/*/PackageInfo` with PlistBuddy.
- **Architectures:** when upstream ships both (`App-arm64.dmg`, `App-x64.dmg`), use one
  cask with `arch arm: "arm64", intel: "x64"`, `#{arch}` in the URL and
  `sha256 arm: "...", intel: "..."`. A single-architecture build needs
  `depends_on arch: :arm64` or `:x86_64`; a universal build needs none.
- **`depends_on macos:`:** if the online audit says the floor is higher than the
  bundle's `LSMinimumSystemVersion`, pin it (`depends_on macos: :big_sur`); drop an
  empty value.
- **`zap` and `caveats`:** delete an empty `zap trash: ""`; add `caveats` when the app
  needs permissions or Gatekeeper approval.
- **No release yet:** start with `brew create --cask --tap <owner>/<tap> --no-fetch
  --set-name <token> --set-version 0.0.0 <expected asset url>` (it skips the download
  and templates the version into the URL), then set `sha256` to 64 zeros and fill the
  rest. The first `brew bump-cask-pr` refreshes only version and checksum, so a wrong
  tag or file-name pattern is not corrected. Such a cask is not installable: do not
  claim it works until a real release exists, the first bump has run and the cask has
  passed an audit.

## Ships both

A Python CLI and a prebuilt app of the same name give `Formula/<name>.rb` and
`Casks/<name>.rb`. Plain `brew install <name>` is then ambiguous; add a note to
the tap README distinguishing `brew install --formula` from `--cask`.

## After creating

1. Review the description, license, URLs, test command, bundle names and
   dependencies once more.
2. Run `mise run generate-readme` in the tap and commit the regenerated package
   table with the Ruby file; CI fails a stale table.
3. Invoke `homebrew-verify` for the pre-PR gate: audit, install and test
   evidence, catalog freshness and local checks. If skills are not
   auto-discovered, read its sibling `SKILL.md`.

Follow the tap's own `AGENTS.md`, `CONTRIBUTING.md` and PR template for branch
names, commit titles and review flow, and include the verification evidence in
the PR body. Pushing and opening the PR follow the user's approval rules.
