# Dispatch report

A guide to the evidence, not a file to create on every run. Keep `passed`,
`pending`, and `skipped` distinct. Never record a token value.

- **Tap and producer:** `owner/homebrew-<tap>`, the producer repository, the
  formula or cask and its registry name
- **Classification:** `standard-job`, `other-dispatch`, `template-owned` or `none`

## Checks

| Check | Evidence | Result (`passed` / `failed` / `pending` / `skipped`) |
|---|---|---|
| Name exists in the tap (`Formula/` or `Casks/`) | | |
| Receiver event type and payload keys read from the tap | | |
| Producer cloned and classified | | |
| Job rendered by `bump_job.py` and inserted, or `copier update` reviewed | | |
| Workflow lint (`actionlint` or `zizmor`), if installed | | |
| `HOMEBREW_TAP_TOKEN` exists in the producer (`gh secret list`, names only) | | |
| Branch pushed and pull request opened (each approved) | | |
| First release fired the dispatch and the tap opened its PR | | |

## Token

The secret name, the scope the user must grant (the tap only, Contents: write) and
whether it exists now. State that releases skip the bump until it does.

## Blockers
