# Verification report

A guide to the evidence, not a file to create on every run. Keep `passed`,
`pending`, and `skipped` distinct.

- **Verdict:** ready / blocked / locally checked, buildability unverified
- **Tap and revision:** `origin` identity, base, head SHA
- **Affected items:** formulae and casks, including same-named pairs

## Checks

| Check | Command or source | Result (`passed` / `failed` / `pending` / `skipped`) |
|---|---|---|
| `desc`, SPDX `license`, `livecheck`, `test do` | | |
| Extras marker intact (formulae with extras) | | |
| Cask URL, checksum, `app`/`pkg` stanza | | |
| `brew audit --strict --online` | | |
| `brew install --build-from-source` and `brew test` | | |
| README regeneration | | |
| Local gate (`mise run check`) | | |

## CI evidence

`tests.yml` run URL and head SHA, with the `tap-syntax`, `build-bottle` and
`cask-audit` results, or the local command and result. State `pending` when
unavailable.

## Blockers and intentional skips

Each with its reason and what would clear it.
