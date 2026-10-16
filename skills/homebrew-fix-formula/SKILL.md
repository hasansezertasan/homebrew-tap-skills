---
description: Repair an existing formula or cask in this Homebrew tap by editing it when livecheck stops matching upstream, resources or checksums drift, brew audit or brew test fails, a cask URL, checksum or app/pkg stanza no longer matches the release, or a seeded placeholder needs activating. Keep the livecheck block and the extras marker intact, then invoke homebrew-verify for the readiness verdict.
name: homebrew-fix-formula
---

# Repair a Formula or Cask

Read the [template contract](references/contract.md) for the task names and paths
this skill relies on.

Repair the affected item without re-scaffolding over curated metadata. Derive tap
identity from `origin`, the Actions context or an explicit `HOMEBREW_TAP`. Read the
Ruby file, the relevant update workflow, and the upstream release or PyPI
release before editing. Read [references/repair-cases.md](references/repair-cases.md)
for repository evidence and the update workflows' limits; its examples are
derived from the workflows and scaffolder tests, not recorded failed installs.

## 1. Reproduce and classify

Record the failing command or workflow run and head SHA, the current version, the
upstream response and the affected macOS or architecture. Run the audit by name,
not file path: `brew audit --strict --online <owner>/<tap>/<name>` (add `--cask`
for a cask). Distinguish version discovery (`livecheck`), resource or checksum
drift, audit style failures, build or test failures, and cask stanza mismatches. A
Cobo `.gitignore` drift failure is a managed-sync problem, not a formula defect;
use the sync process instead of editing it.

Check the real upstream response status and content. A rate limit, missing
release or HTML error page is not a new asset or a reason to loosen a livecheck
regex. Preserve the existing version policy and investigate a lower upstream
version rather than forcing a downgrade.

## 2. Repair version discovery

- Keep the `livecheck` block: it powers `brew livecheck --json`, which the weekly
  and dispatch workflows read. A formula uses `url :stable` with `strategy :pypi`;
  a cask uses `github_latest`. Make the narrowest change that selects the intended
  stable release.
- Run `brew livecheck --json <owner>/<tap>/<name>` (`--cask` for a cask) and
  compare `version.current` and `version.latest` with upstream. A livecheck that
  prints nothing or an error means discovery is broken; the workflows swallow that
  output and treat it as "no update".
- Never remove or hardcode around `livecheck` to make a bump appear.

## 3. Repair formula resources and checksums

For a formula that uses `virtualenv_install_with_resources`, regenerate resources
with `brew update-python-resources`, not by hand-editing resource blocks. Read
the `# homebrew-tap:extras=<extras>` comment first and pass it so extras-only
resources survive:

```sh
brew update-python-resources --package-name="<name>[<extras>]" <owner>/<tap>/<name>
```

Without an extras marker, run it without `--package-name`. Do not delete the
marker. A resource whose sdist is missing, or a dependency that now ships only
platform wheels, is an upstream or packaging blocker: report it instead of
pinning a wheel that does not build everywhere. Compare each resource URL with
its checksum from the PyPI sdist, and never copy a checksum from a failed
install message without checking the downloaded bytes.

For a version bump, run the bump command and flags the tap's update workflow
uses (read `update-formulas.yml`), writing the file without opening a PR. It
keeps a changed URL and checksum together. After any edit, rebuild from source
and test: audit alone is not enough to prove the resources build.

## 4. Repair casks

Select the real asset for the version, download it, and compute its SHA-256 from
those bytes. Keep the URL version-templated, so `brew bump-cask-pr` can rewrite
it. Check:

- the `app` bundle name inside a `.dmg` or `.zip`; a `pkg` stanza needs a matching
  `uninstall pkgutil:` identifier;
- `depends_on macos:` and `depends_on arch:` against the asset and the bundle's
  `LSMinimumSystemVersion`;
- that a percent-encoded asset name in the URL still resolves to the file the
  checksum was taken from.

Run `brew audit --cask --strict --online <owner>/<tap>/<name>` and fix style
failures it names. Casks are not built into bottles.

## 5. Handle seeded placeholders

A seeded cask has version `0.0.0` and a zero checksum. Activate it only when a
real release exists and its asset, checksum and stanzas have been verified; the
first `brew bump-cask-pr` fills the version and checksum. If no release exists,
leave the placeholder recognizable, report activation blocked and installation
intentionally skipped, and never fabricate a digest.

## 6. Fix audit and test failures

Fix the specific audit message. Frequent ones: a description that is not
capitalized or ends in a period, a non-SPDX license, a `test do` that assumes
`--version` when the CLI differs, missing `depends_on` for a system library.
Prefer the scaffolder's conventions; if the fix is regenerating, re-run
`homebrew-add`'s scaffolder in a scratch location and port only the fields that
changed rather than overwriting curated ones.

## 7. Finish with homebrew-verify

Invoke `homebrew-verify`. Regenerate the README (`mise run generate-readme`) and
run the local gate. Require current-head `tests.yml` evidence (and a local
`brew install --build-from-source` and `brew test` for a changed formula) when
resources, URLs, checksums, dependencies or the test changed; record it pending
if unavailable.

Report the root cause, evidence source, repairs, the livecheck result before and
after, and verification results. Keep passed, pending and skipped separate.
Describe remaining upstream or tooling blockers explicitly, and follow the user's
approval rules for remote actions.
