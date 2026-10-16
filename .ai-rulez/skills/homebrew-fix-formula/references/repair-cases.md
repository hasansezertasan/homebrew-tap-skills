# Repair Evidence and Cases

The template's tap starts with no formulae or casks, so the cases below are
derived from the update workflows and the scaffolder tests, not from recorded
failed installs of published formulae. Repository identity in operational
commands still comes from the current remote or an explicit override.

## Evidence map

| Behavior | Locator |
| --- | --- |
| Weekly formula update: livecheck, bump, resources, audit, build, test, revert on failure | `template/.github/workflows/update-formulas.yml`, `update-formulas` job |
| Dispatch formula update, same steps without the revert | `update-formula-dispatch.yml`, "Update formula" |
| Cask update: livecheck `--cask`, `bump-cask-pr`, audit, revert on failure | `update-casks.yml`, `update-casks` job |
| Extras marker read by both formula workflows | `sed -n 's/^[[:space:]]*# homebrew-tap:extras=//p'` in the update workflows |
| Formula scaffolder rendering, extras comment, SPDX marker, sdist-only pinning | the `homebrew-add` skill's `scripts/add_formula.py`; `tests/test_add_formula.py` |
| Cask scaffolder: URL kept percent-encoded, arch stanza, `.pkg` needs an id | `scripts/add_cask.py`; `tests/test_add_cask.py` |
| Bottle build for changed formulae, cask audit for casks | `tests.yml`, `build-bottle` and `cask-audit` jobs |

## Workflow-derived cases

| Case | Failure to check for | Response |
| --- | --- | --- |
| The weekly formula job bumps a formula but resolution, audit, build or test fails | The job prints a warning, runs `git checkout -- Formula/<name>.rb`, and continues; the PR can open without that formula and the run can still succeed | Read the per-formula `::warning::` lines in the log, not the final job status; repair that formula with `brew update-python-resources` and a source build |
| A formula scaffolded with `--extras` loses resources after a bump | The extras comment was deleted or edited, so the update re-resolved the base requirement | Restore `# homebrew-tap:extras=<extras>` and re-run `brew update-python-resources --package-name="<name>[<extras>]"` |
| `brew livecheck` prints an error or nothing | The workflow does `2>/dev/null || echo "[]"`, so a broken livecheck reads as "up to date" | Run the command locally and read the real error before concluding no update exists |
| Cask audit fails after `bump-cask-pr` | The weekly cask job reverts the cask and warns; the dispatch job fails | Fix the stanza or URL pattern named by the audit; keep the URL version-templated |
| A cask asset name contains a space or other encoded character | A rebuilt URL no longer matches the checksummed file | Keep the URL as the API reported it, percent-encoded, and recompute the checksum from that download |
| A `.pkg` cask fails `brew audit --cask --strict` | `pkg` without `uninstall pkgutil:` | Add the package identifier read from the asset |
| A dependency ships only a platform wheel | The scaffolder refuses to pin it; a bump may fail | Report the packaging blocker rather than pinning a wheel |
