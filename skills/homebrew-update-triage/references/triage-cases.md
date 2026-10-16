# Triage Evidence

The template's tap starts with no formulae or casks. The cases below are derived
from the update workflows and Homebrew's documented behavior, not from observed
failed runs of a published tap; label them that way when reporting.

## Workflow boundaries

| Behavior | Locator |
| --- | --- |
| Weekly formula job: check job, then update job (macOS) with revert-and-warn per formula | `template/.github/workflows/update-formulas.yml` |
| Weekly job skips `deprecate!` / `disable!` formulae, casks have no such skip | `update-formulas.yml` versus `update-casks.yml` |
| Weekly `dry_run` suppresses PR creation (`inputs.dry_run != true`) | both weekly workflows |
| Dispatch payload validation and `$GITHUB_ENV` hand-off | `update-formula-dispatch.yml`, `update-cask-dispatch.yml`, "Validate payload" |
| Dispatch formula job fails without a failure issue; the cask job opens one (`issues: write`) | `update-cask-dispatch.yml`, "Report failure" |
| PRs opened with `GITHUB_TOKEN` do not trigger `tests.yml` | PR bodies in all four workflows; GitHub docs on the built-in token |
| Branches: `auto-update/formulas`, `auto-update/casks`, `auto-update/<name>`, `auto-update/cask-<name>` | the "Create Pull Request" steps |

## Cases

| Case | Handling |
| --- | --- |
| A scheduled formula run is green but one formula did not update | Read the per-formula warnings; the job reverted it and continued. Repair through `homebrew-fix-formula`. |
| Livecheck errors are hidden | `2>/dev/null \|\| echo "[]"` makes failure look like "up to date"; run livecheck locally. |
| Dispatch for a valid but unknown token | Fails with "not found"; the token must match an existing file. |
| Dispatch carries a version | It is passed to the bump as given, not checked against livecheck; verify it exists upstream. |
| Update PR has no bottles | Expected for `GITHUB_TOKEN` PRs; close and reopen to run `tests.yml`, then label `pr-pull`. |
| Branch protection blocks the bot PR | A policy problem, not an updater defect; report it and do not widen permissions. |
