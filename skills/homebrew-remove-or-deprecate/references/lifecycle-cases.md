# Lifecycle Evidence

These cases explain the boundaries of retiring a formula or cask. The template's
tap is empty and its history contains no committed formulae or casks; the cases
below come from the workflows and Homebrew's documented behavior, not from
observed retirements. Repository identity in operational commands still comes
from the current remote or an explicit override.

## Repository boundaries

| Behavior | Locator |
| --- | --- |
| Weekly formula job skips files containing `deprecate!` or `disable!` | `template/.github/workflows/update-formulas.yml`, "Check for formula updates" (`grep -qE '^\s*(deprecate\|disable)!'`) |
| Weekly cask job has no such skip | `update-casks.yml`, "Check for cask updates" |
| Dispatch workflows reject a missing file | `update-formula-dispatch.yml` / `update-cask-dispatch.yml`, "Validate payload" (`Formula/<name>.rb` or `Casks/<name>.rb` must exist) |
| Catalog is built from the files present | `scripts/gen_readme_packages.py` (`collect("Formula")`, `collect("Casks")`); a formula and cask of one name merge into one row |
| Bottles apply to formulae only | `tests.yml`, `build-bottle` (formulae) versus `cask-audit` |

## Native Homebrew behavior: source evidence, not `brew` runs

Inspected `Homebrew/brew` at `dbdc9b534eead3bbc7c741956e8893fac4b6914e`
(2026-10-16, `main`; no tag describes it). The locators are paths in that
repository. Recheck the user's installed Homebrew revision before claiming
observed behavior.

- `Library/Homebrew/formula.rb` (`deprecate!`, `disable!`) and
  `Library/Homebrew/cask/dsl.rb` (`deprecate!`, `disable!`): both take `date:`
  and `because:`, plus at most one replacement. A future `deprecate!` date does
  not deprecate yet. A future `disable!` date deprecates the item until then and
  disables it afterwards (unless a `deprecate!` is also present).
- [Deprecating, Disabling and Removing](https://docs.brew.sh/Deprecating-Disabling-and-Removing)
  (`docs/Deprecating-Disabling-and-Removing.md`): deprecated warns and
  proceeds, disabled errors, and removal follows a year after the disable date
  in `homebrew/core` and `homebrew/cask`. A tap decides its own policy.
- `Library/Homebrew/tap.rb` (`formula_renames`, `cask_renames`,
  `tap_migrations`): `formula_renames.json` and `cask_renames.json` map an old
  name to a new one inside the tap; `tap_migrations.json` maps a name to another
  tap or name. `formulary.rb` and `cask/cask_loader.rb` consult them in that
  order. `docs/Rename-A-Formula.md` and `docs/Migrating-A-Formula-To-A-Tap.md`
  describe the same split.
- `Library/Homebrew/cask/audit.rb`: a cask whose token is listed in
  `tap_migrations.json` fails audit, so add the entry only when the file is gone.
- Removing a file does not uninstall it for existing users.

The documentation page used to be named
`Deprecating-Disabling-and-Removing-Formulae`; recheck the URL if it moves again.

## Cases

| Case | Handling |
| --- | --- |
| Upstream project abandoned; users should keep working for now | Deprecate with a `because:` and agreed date; the weekly formula job stops checking it, a cask keeps being checked |
| Upstream removed its macOS release but the PyPI CLI lives | Retire only the cask; keep the formula; confirm no dependent or README row still points at the cask |
| Python CLI renamed upstream | Add the new formula with `homebrew-add`, record a `formula_renames.json` entry (`{"old": "new"}`) once the new one exists, then remove the old file. Use `tap_migrations.json` only to move it to another tap |
| A producer still dispatches `update-formula` for a removed formula | The dispatch run fails validation; coordinate the producer change |
| The README table still lists a removed item | Regenerate with `mise run generate-readme`; prose outside the markers is edited by hand |
