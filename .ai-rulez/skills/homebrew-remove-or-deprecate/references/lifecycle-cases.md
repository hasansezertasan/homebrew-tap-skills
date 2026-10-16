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

## Native Homebrew behavior

Checked against Homebrew's documentation; recheck the user's Homebrew revision.

- [`deprecate!` and `disable!`](https://docs.brew.sh/Deprecating-Disabling-and-Removing-Formulae):
  both take `date:` and `because:`; `disable!` stops installation.
- Removing a formula does not uninstall it for existing users, and renames or
  moves are expressed with `tap_migrations.json` at the tap root.

## Cases

| Case | Handling |
| --- | --- |
| Upstream project abandoned; users should keep working for now | Deprecate with a `because:` and agreed date; the weekly formula job stops checking it, a cask keeps being checked |
| Upstream removed its macOS release but the PyPI CLI lives | Retire only the cask; keep the formula; confirm no dependent or README row still points at the cask |
| Python CLI renamed upstream | Add the new formula with `homebrew-add`, record a `tap_migrations.json` entry for the old name only after the new one exists, then remove the old file |
| A producer still dispatches `update-formula` for a removed formula | The dispatch run fails validation; coordinate the producer change |
| The README table still lists a removed item | Regenerate with `mise run generate-readme`; prose outside the markers is edited by hand |
