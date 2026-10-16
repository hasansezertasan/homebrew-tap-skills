# Triage report

A guide to the evidence, not a file to create on every run. Keep `passed`,
`pending`, and `skipped` distinct. Redact credentials.

- **Cause and confidence:** one line, and how sure
- **Workflow, event and run:** file, run URL, head SHA, current branch SHA
- **Targets:** formulae or casks selected, and any dispatch version

## Stages

| Stage | Evidence | Result (`passed` / `failed` / `pending` / `skipped`) |
|---|---|---|
| Payload validation (dispatch) | | |
| `brew livecheck --json` discovery | | |
| Bump (`bump-formula-pr` / `bump-cask-pr`) | | |
| Resource regeneration (formulae) | | |
| Audit, source build, test | | |
| PR creation | | |

## Partial updates

Which formulae or casks were reverted with a warning, and which landed in the PR.

## Action and verification

What was repaired or left alone, the `homebrew-verify` verdict, and any approved
retry. State `pending` when evidence is unavailable.

## Blockers

Each with its reason and what would clear it.
