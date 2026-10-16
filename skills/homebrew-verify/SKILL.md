---
description: 'Decide whether a Homebrew tap change is verified and ready - run the read-only pre-PR readiness gate after adding, updating, repairing, or removing a formula or cask, and report the verdict with the evidence. Use for readiness verdicts and verification reports: brew audit, source build and test, livecheck, extras marker, placeholder casks, README catalog freshness and whether bottle or macOS install evidence is needed. It never edits formulae or casks; that is homebrew-fix-formula''s job.'
name: homebrew-verify
---

# Verify a Homebrew Tap Change

Read the [template contract](references/contract.md) for the task names and paths
this skill relies on.

Use this gate after formula or cask work, including `homebrew-add`, and before
reporting a change ready for review. Read the changed Ruby files and the relevant
workflow steps; the local gate alone does not prove that a formula builds or a
cask installs.

## 1. Establish the scope

Inspect the diff against the intended base and identify changed formulae and
casks, same-named pairs, and shared scripts or workflows that affect them. Get
the tap identity from `origin` (`owner/homebrew-<tap>` is `owner/<tap>`) or an
explicit `HOMEBREW_TAP`; never copy this template's owner into another tap. For
an empty tap, report that there are no packages to build or install.

Read [references/verification-cases.md](references/verification-cases.md) when
diagnosing failed verification or deciding what evidence a change needs. It
separates observed workflow behavior from workflow-derived examples.

## 2. Check the Ruby files

- **Formulae:** confirm `desc` is capitalized with no trailing period, `license`
  is a real SPDX identifier (not `TODO-set-SPDX-license`), `livecheck` is present
  (`url :stable`, `strategy :pypi`), and the `test do` block runs the CLI's real
  smoke command. When the formula was scaffolded with extras, confirm the
  `# homebrew-tap:extras=` comment is intact, because the update workflows read it.
  Resources must come from `brew update-python-resources` or the scaffolder, never
  hand-edited.
- **Casks:** confirm the version-templated URL, the checksum for the exact
  asset, the `app` bundle name or `pkg` plus `uninstall pkgutil:`, `depends_on`
  stanzas, and `livecheck`. A percent-encoded asset name must still resolve to
  the file the checksum was taken from.
- **Placeholders:** a seeded cask (version `0.0.0`, zero checksum) is not
  installable. Record installation as intentionally skipped; do not call a skipped
  or empty `cask-audit` successful.
- A same-named formula and cask make plain `brew install <name>` ambiguous; check
  the README says how to pick one.

## 3. Run the local gate

```sh
mise install
mise run generate-readme
mise run check
```

Review the generated README diff. `check` runs unit tests, README freshness,
YAML and workflow linting (including zizmor) and Cobo drift; it does not run
`brew`. Resolve failures according to their source. For drift in files the
template manages (such as `.gitignore`), use the template's sync process instead
of editing them by hand. Re-run the gate after fixes.

Then run Homebrew's own checks where Homebrew is available:

```sh
brew audit --strict --online <owner>/<tap>/<name>
brew audit --cask --strict --online <owner>/<tap>/<name>
brew install --build-from-source <owner>/<tap>/<name>
brew test <owner>/<tap>/<name>
brew test-bot --only-tap-syntax
```

Audit by name, not by file path, and use the cask form for casks. Build from
source and run `brew test` for a changed formula; these are slow and need the
tap installed under Homebrew's `Library/Taps` (`brew tap <owner>/<tap> <path>`).
If `brew` is unavailable, report each of these as `pending`, not passed.

## 4. Decide and record CI and install evidence

Require a real build or install for a new formula or cask and for changes to URLs,
checksums, resources, dependencies, the test, the `app`/`pkg` stanza or
`depends_on`. `tests.yml` can provide this evidence: `tap-syntax` runs
`brew test-bot --only-tap-syntax`, `build-bottle` builds bottles for formula
changes, and `cask-audit` audits every cask. Check results for the exact head SHA
and the affected items; an unrelated run, a skipped job, or a draft PR where
`build-bottle` and `cask-audit` do not run is not evidence. A PR opened with the
built-in token does not trigger `tests.yml`; close and reopen it or push to run it.

Metadata-only, removal-only and skill-only changes normally need the local gate
without a new build. For a seeded cask, record the intentional install skip and
require verification once a real release activates it. If evidence is needed but
unavailable, mark it pending and report the change as locally checked, with
buildability or installability unverified. Triggering a remote workflow, pushing
or opening a PR follows the user's approval rules. Bottle publication (`pr-pull`)
is a later maintainer step, not part of this gate.

## Report

Use the [verification report](references/verification-report.md) as a guide.
Summarize the affected formulae and casks, local commands and results,
audit/build/test results, `tests.yml` evidence (run URL and head SHA, or local
command results), the extras marker and README checks, blockers and intentional
skips. Keep `passed`, `pending` and `skipped` distinct so a maintainer knows what
remains.
