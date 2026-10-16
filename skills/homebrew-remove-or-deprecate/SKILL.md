---
description: Remove, deprecate or disable a formula or cask in this Homebrew tap when retiring an upstream tool, dropping a packaging route, or replacing a package. Establish deprecate!/disable! versus deletion, identify the exact items and any same-named formula and cask pair, preserve dependents, handle renames with tap_migrations.json, regenerate the README catalog, and finish with homebrew-verify.
name: homebrew-remove-or-deprecate
---

# Remove, deprecate or disable a formula or cask

Read the [template contract](references/contract.md) for the task names and paths
this skill relies on.

## Establish the intended outcome

Read `AGENTS.md`, the selected Ruby file, `scripts/gen_readme_packages.py` and the
applicable workflows before changing files. Read
[lifecycle evidence](references/lifecycle-cases.md) for repository boundaries and
native Homebrew behavior. Derive repository identity from the remote, Actions
context or an explicit override, and preserve local work.

Confirm the exact formula or cask, upstream identity, reason, and any
replacement. If the request says only "retire", "drop" or "deprecate" without a
clear outcome, ask through the native question tool before acting:

- **Deprecation:** add `deprecate! date: "YYYY-MM-DD", because: "..."` (a
  replacement formula or cask, or an `:unmaintained`-style reason). The item
  stays installable, and `brew` warns users who install or upgrade it.
- **Disabling:** add `disable! date: "YYYY-MM-DD", because: "..."`. Installation
  is refused; already installed copies keep working until removed. Use it after a
  deprecation period, or when installing is actively harmful.
- **Removal:** delete the file. Existing installs are not uninstalled, users get
  an error on update or reinstall, and history remains in Git.
- **Rename or move:** a tap-level `tap_migrations.json` entry redirects the old
  name to the new name or tap; deleting the old file alone does not migrate users.

Explain that none of these uninstall or migrate an installed package by
themselves. Verify the user's Homebrew revision and any claim about `brew`
warning text before making runtime claims; do not promise an absolute install
prohibition (a user can still install from a direct URL or an older commit).

## Bound the item set and references

Inspect `Formula/<name>.rb` and `Casks/<name>.rb`. A project that ships both has
a same-named formula and cask: confirm which one is being retired and keep the
other unless the user says otherwise. A failed cask update is not evidence that
the formula should retire, and the reverse. Compare homepage, source URL and
description to establish a real relationship; do not infer identity from a name
prefix or remove every file sharing one.

Search surviving formulae and casks for reverse references: `depends_on`
lines, `conflicts_with`, `caveats` and `uninstall` text naming the retiring token.
Inspect README prose outside the generated markers, update workflow inputs,
pending `auto-update/*` PRs and any producer that dispatches `update-formula` or
`update-cask` for this name. Resolve affected dependents with the user before
leaving a broken graph; do not substitute a replacement dependency unless it is
compatible.

Put approved reason, replacement and user-action guidance in the `because:` text
and in existing README prose outside the generated markers. Do not write
guidance that promises migration the change does not perform.

## Make the approved lifecycle edit

- **Deprecate or disable:** edit the Ruby file in place; keep the formula or cask
  otherwise unchanged, including its `livecheck` block and any
  `# homebrew-tap:extras=` marker. Do not manufacture a placeholder version or
  checksum. Use the date the user agrees; do not invent a future disable date.
- **Remove:** delete the exact file and nothing else. Do not touch an unrelated
  package, shared dependency or the directory scaffolding (`Formula/README.md`,
  `Casks/README.md`).
- **Rename or move:** add the `tap_migrations.json` entry as agreed and confirm
  the replacement exists before pointing at it.

Account for automation. The weekly formula job skips any formula whose file
contains a `deprecate!` or `disable!` line, so an edit keeps it out of weekly
bumps; the weekly cask job and both dispatch workflows do not skip, so a
dispatching producer or a cask can still open update PRs for a deprecated item.
Deleting the file makes the dispatch workflows fail validation ("not found").
Coordinate producer dispatch changes and pending update PRs with approval
instead of silently changing external automation or reintroducing a retired item.

## Regenerate and verify

Regenerate the catalog with `mise run generate-readme`; the table is built from
`Formula/*.rb` and `Casks/*.rb`, so a deleted file leaves it and a deprecated one
stays. Inspect that only the approved rows changed and surviving items remain.
Finish with `homebrew-verify`, including `mise run check`.

Deprecation and removal normally need the local gate, not a fresh build. A
retained or replacement item whose dependencies, URLs or test changed needs
install and test evidence under `homebrew-verify`. Claims about installed-package
behavior need separate runtime evidence. Invoke `homebrew-fix-formula` for any
retained or replacement repair.

Report the exact retained, edited and deleted paths, the reason, sibling
formula-or-cask decisions, dependent and reference handling, replacement and
user guidance, automation consequences, verification passed/pending/skipped and
remaining blockers. Keep publishing and external changes subject to the user's
approval.
