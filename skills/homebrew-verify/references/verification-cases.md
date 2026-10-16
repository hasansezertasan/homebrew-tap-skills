# Verification Evidence

These cases explain why the gate goes beyond the local unit tests and README
check. The template's tap is empty, and its history contains no committed
formulae or casks. The examples below come from the workflows and the scaffolder
tests, not from observed failed builds of published formulae. Repository identity
in operational commands still comes from the current remote or an explicit
override.

## Workflow boundaries

| Behavior | Locator |
| --- | --- |
| `tap-syntax` runs on every PR and push; `build-bottle` only for PRs that change `Formula/*.rb` and are not drafts; `cask-audit` for non-draft PRs | `template/.github/workflows/tests.yml` |
| `cask-audit` audits every cask in the tap, not only the changed one | `tests.yml`, "Audit casks" |
| README catalog freshness and Cobo checks | `template/.github/workflows/scripts.yml` |
| Local gate coverage | `template/.config/mise.toml`, `check` |

## Workflow-derived cases

| Evidence | Failure to check for | Gate response |
| --- | --- | --- |
| `tests.yml` path filter and draft condition | A draft PR or a change outside `Formula/**` and `Casks/**` never builds a bottle or audits casks | Require evidence for the exact head SHA and affected items; do not treat an absent job as passed |
| Update PRs opened with `GITHUB_TOKEN` | No `tests.yml` run exists | Close and reopen the PR or push to run it |
| `scripts/add_formula.py` SPDX handling (`tests/test_add_formula.py`) | A non-SPDX PyPI license leaves `TODO-set-SPDX-license` | `brew audit --strict` rejects it; set the real identifier |
| `scripts/add_formula.py` default test command | `test do` assumes `<name> --version` | Check the CLI's real version command |
| `scripts/add_formula.py` extras comment | Editing or deleting `# homebrew-tap:extras=` drops extras-only resources on the next bump | Confirm the comment matches the scaffolded extras |
| `scripts/add_cask.py` `.pkg` handling (`tests/test_add_cask.py`) | `pkg` without `uninstall pkgutil:` fails `brew audit --cask --strict` | Confirm the package identifier |
| Seeded cask (version `0.0.0`, zero checksum) | Cannot install | Record the install skip; require verification after the first real release |
| Same-named formula and cask | `brew install <name>` is ambiguous | Check the README note |
