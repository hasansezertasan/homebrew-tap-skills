# Setup report

A guide to the evidence, not a file to create on every run. Keep `passed`,
`pending`, and `skipped` distinct. Never record secret values.

- **Outcome level:** plan / rendered locally / repository configured / first package published
- **Destination:** `owner/homebrew-<tap>`, visibility, default branch
- **Template:** source and version from `.copier-answers.yml`
- **Checkout identity:** `origin`, and any `HOMEBREW_TAP` / `HOMEBREW_TAP_DIR` overrides

## Rendered versus configured separately

| Item | Where it lives | Result (`passed` / `failed` / `pending` / `skipped`) |
|---|---|---|
| Files rendered, `.copier-answers.yml` committed | checkout | |
| README title, description and LICENSE identity | rendered files | |
| Actions enabled, PR creation allowed, read-only default permissions | repository settings | |
| `pr-pull` label exists, Issues if wanted | repository settings | |
| Producer dispatch token (name and purpose only) | producer repository secret | |
| Renovate or other installed apps | repository settings | |
| Required checks and rulesets | repository settings | |

## First formula or cask

Kind, name, `tests.yml` run for the head SHA (`tap-syntax`, `build-bottle` or
`cask-audit`), bottle state, and the `homebrew-verify` verdict with its head SHA.
State `pending` when install evidence is unavailable.

## Blockers and intentional skips

Each with its reason and what would clear it.
