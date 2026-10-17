# 0002: Adopt the copier-skill-repo template

Status: accepted. Date: 2026-10-17.

This repo's scaffold now comes from the
[`copier-skill-repo`](https://github.com/hasansezertasan/copier-skill-repo) template (v0.2.0)
and is updated with `copier update`, following the same recipe as
`scoop-bucket-skills`. The skills and `CHANGELOG.md` were not touched, and
`README.md` only had its Development commands updated. This record lists what
still differs from a plain render and why; it is not updated as the project
evolves.

## Replaced by the template's version

- **Version source.** `pyproject.toml` carried the version only because
  release-please updated it natively. `package.json` now does, and
  `pyproject.toml` is gone. Nothing has been released yet, so the version and the
  release manifest (now at the repo root) start at the template's `0.0.0`, and the
  first release is `0.1.0` through `initial-version`. The generated plugin
  manifests therefore read `0.0.0` until that release. The open release PR is
  rebuilt by release-please on the next push to `main`. This moves the plugin
  version back from the `0.1.0` it read before: `docs/host-support.md` records
  installs of that unreleased `0.1.0`, which were evidence about a pre-release
  tree, not a release.
- **Release guard.** `scripts/release_guard.py` and its test are replaced by the
  template's `release-merge.mjs` and `release-guard.mjs`, which implement the same
  sole-pending-release rule and add a version-drift check.
- **Release configuration.** `.config/release-please-config.json` and
  `.config/release-please-manifest.json` moved to the repo root as the template
  places them, with `extra-files` bumping the plugin manifests.
- **CI and release workflows, Renovate config, `.node-version`,
  `scripts/check-repo.mjs`.** Taken as rendered. Renovate now extends
  `local>hasansezertasan/renovate-config`, which ADR 0001 had deliberately not
  adopted. The old `check` workflow's `ref`
  input is gone: the template's release workflow regenerates the plugin output on
  the release PR branch itself.
- **Required check name.** The check job is now `check`, not `validate`. Branch
  protection on `main` must require `check` instead; that setting lives on GitHub,
  so this change does not make that edit. Change it when merging: until then
  the old `validate` requirement never reports and every PR stays blocked.
- **Task runner.** The mise tasks are gone: `npm run generate`, `npm run check`,
  `npm test` and `npm run eval` replace `agents:generate`, `check`, `test` and
  `agents:eval`. ai-rulez 5.3.0 is pinned in `package.json` instead of mise.
- **Antigravity and Pi.** The render adds the root `plugin.json` adapter and the
  `pi-package` keyword and `pi.skills` entry in `package.json`.
  `docs/host-support.md` lists both as not evaluated.

## Differences kept on purpose

- **`publish_to_npm: false`.** The package is `"private": true` and nothing is
  published to a registry, as before.
- **`.ai-rulez/config.toml`.** The custom `AGENTS.md` preset, the AR401 and AR402
  opt-outs (the skills cite files of the tap they operate on),
  `shared_resources = ["references"]` and the plugin text stay. `version_from`
  became `package.json`, the comments name the npm commands, and `AR9T0` is off as
  the template turns it off for the Antigravity adapter. That rule also catches
  `.mcp.json` and `hooks/` at the root, which nothing guards now; the context note
  says so and points at copier-skill-repo#43.
- **Python unit tests and eval.** `npm test` runs `tests/` with `python -B`, and
  `check.yml` has one extra step for them, because the template ships no tests.
  The npm script needs a `python` on `PATH` (`mise install` provides one from
  `.config/mise.toml`); the CI step uses `python3`.
  `npm run eval` is the former `agents:eval` task (offline, informational, not a
  gate).
- **mise.** `.config/mise.toml` keeps only the tool pins: Python, and the
  Renovate-tracked Copier version that `tests/test_copier_pin.py` keeps equal to
  the one in `homebrew-tap-setup`.
- **`CONTRIBUTING.md` and `docs/installation.md`.** The template's versions plus
  repo-specific content: a "Homebrew Tap Skills development" section, and the
  install prompt with its "Then use it" table. The OpenCode config snippet uses
  the `skills.paths` object that this repo's own `opencode.json` uses, where the
  template shows a bare array; OpenCode's published docs show neither shape. They are template-owned, so
  future template changes merge into them.
- **`.ai-rulez/context/homebrew-tap-skills.md`.** Names the npm commands and the
  `package.json` version source, so the regenerated `AGENTS.md` matches. The skills
  still cite the tap's own `mise run` tasks; those belong to the tap they operate
  on, not to this repo.
- **`.gitignore`.** The template's `node_modules/` plus
  `.ai-rulez/.generated-manifest.local.json` and `__pycache__/`.
- **`.copier-answers.yml` keeps `placeholder_skill: hello`.** The placeholder
  skill is not present here; Copier leaves a deleted file deleted unless the
  template changes it.
