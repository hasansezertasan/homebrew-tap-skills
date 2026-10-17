# 0001: Mirror scoop-bucket-skills

Status: accepted; partly superseded by [0002](0002-adopt-the-copier-skill-repo-template.md): the version source is now `package.json`, Renovate extends the shared preset, and the required check is `check`. Date: 2026-10-16.

[`scoop-bucket-skills`](https://github.com/hasansezertasan/scoop-bucket-skills)
is the reference for how this plugin is packaged, released and evaluated, and
[`copier-homebrew-tap`](https://github.com/hasansezertasan/copier-homebrew-tap)
mirrors `copier-scoop-bucket` the way this repository mirrors it. This record
keeps the reasons; it is not updated as the project evolves.

## Decision

- **Same structure, Homebrew content.** Skills are authored in `.ai-rulez/` and
  generated into root `skills/` with Claude and Codex manifests and catalogs,
  one version source (`pyproject.toml`), release-please with the validated-merge
  guard, and unfiltered reusable CI. The six skills map one to one:
  `homebrew-tap-setup`, `homebrew-add`, `homebrew-fix-formula`,
  `homebrew-update-triage`, `homebrew-remove-or-deprecate`, `homebrew-verify`.
- **The scaffolders live here.** `add_formula.py`, `add_cask.py` and
  `tap_name.py` moved from the template into `homebrew-add`, as the Scoop
  manifest scaffolder moved into `scoop-add`. They run against the tap in the
  working directory (`--tap-dir` / `HOMEBREW_TAP_DIR`) because a plugin cannot
  assume its own location is the tap. The previous in-repository `homebrew-add`
  skill was merged into this one.
- **Keep the extras marker contract.** The `# homebrew-tap:extras=` comment the
  formula scaffolder writes is read by the template's update workflows; the
  contract records it so both sides change together.
- **Name.** The repository keeps the `homebrew-` prefix to match
  `scoop-bucket-skills`. Homebrew treats any `homebrew-<x>` repository as a tap,
  so `brew tap hasansezertasan/tap-skills` would resolve here; this repository
  has no `Formula/` or `Casks/`, so that tap would be empty.

## Not adopted

- Evidence recorded for Scoop (host installs, model trials, Windows runs): none
  carries over. [Host support](../host-support.md) and the
  [roadmap](../roadmap.md) start empty.
- `local>hasansezertasan/renovate-config`: not verified to suit this
  repository, so Renovate stays on `config:recommended`.

## Consequences

- The template's scaffolder scripts, their tests and the `add-formula` and
  `add-cask` mise tasks become redundant there and should be removed in the
  template's own change.
- The required status check is `validate`; set branch protection to it.
