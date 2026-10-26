# Template contract

These skills operate on a Homebrew tap made from
[`copier-homebrew-tap`](https://github.com/hasansezertasan/copier-homebrew-tap). They
read the tap's own workflows and README for exact behavior, but rely on the
names and locations below. A template release that changes any of them must bump
the minimum template version recorded here.

Minimum template version: `copier-homebrew-tap` 0.1.0, the first release after
the Copier conversion.

Check the tap against it before relying on the layout below: read `_commit` in
the tap's `.copier-answers.yml`. A tag at or after the minimum (`v0.1.0`, or a
describe form such as `v0.1.0-3-gabc1234`) passes. An older tag predates the
contract, so say so and propose `copier update` with the user's approval; do not
guess at the old layout. A bare hash is indeterminate: it can be a pre-release
render or an untagged ref at or after the minimum. Ask the user which template
revision it was, or check in a template clone that it descends from `v0.1.0`
(`git merge-base --is-ancestor v0.1.0 <hash>`), and propose `copier update` only
when it does not. A tap with no `.copier-answers.yml` predates the Copier
template (it was a GitHub template repository); say so rather than assuming the
layout, and offer adoption through `homebrew-tap-setup`.

## mise tasks

| Task | Used by |
|---|---|
| `generate-readme` | `homebrew-add`, `homebrew-fix-formula`, `homebrew-remove-or-deprecate`, `homebrew-verify` |
| `check` | `homebrew-verify`, `homebrew-remove-or-deprecate` |
| `style:check` | `homebrew-verify` (YAML, Actions and zizmor lint; part of `check`) |

## Files and directories

| Path | Role |
|---|---|
| `Formula/*.rb` | formulae (PyPI-based Python CLIs) |
| `Casks/*.rb` | casks (prebuilt macOS apps) |
| `scripts/gen_readme_packages.py` | README package table, between the `BEGIN`/`END PACKAGES TABLE` markers |
| `.github/workflows/tests.yml` | `brew test-bot`: `tap-syntax`, `build-bottle` (formula changes) and `cask-audit` jobs |
| `.github/workflows/publish.yml` | `brew pr-pull`, triggered by the `pr-pull` label |
| `.github/workflows/update-formulas.yml`, `update-casks.yml` | weekly `brew livecheck` updates, branches `auto-update/formulas` and `auto-update/casks` |
| `.github/workflows/update-formula-dispatch.yml`, `update-cask-dispatch.yml` | `repository_dispatch` types `update-formula` and `update-cask`, branches `auto-update/<name>` and `auto-update/cask-<name>` |
| `.github/workflows/scripts.yml` | README catalog freshness and Cobo boilerplate checks |
| `.github/workflows/zizmor.yml` | workflow security audit |
| `.github/workflows/gitignore-drift.yml` | weekly job that re-renders the Cobo `.gitignore` and opens a pull request on branch `chore/sync-cobo-boilerplate` when it drifted |
| `AGENTS.md` | the tap's invariants; skills read it first |
| `.copier-answers.yml` | recorded template source, version and answers; `copier update` reads it |

## Conventions the workflows read

- A Python formula with extras carries a `# homebrew-tap:extras=<a,b>`
  comment, written by hand when the formula is created. The update workflows pass it to `brew update-python-resources
  --package-name`; without it the first bump drops extras-only resources.
- A formula that uses `virtualenv_install_with_resources` gets
  `brew update-python-resources` during updates; other formulae skip it.
- Update, dispatch and drift jobs open pull requests with
  `secrets.WORKFLOW_TOKEN || secrets.GITHUB_TOKEN`. The secret is optional and
  undefined by default, so the built-in `GITHUB_TOKEN` is used and its pull
  requests start no checks. A producer that dispatches needs its own token (see
  `homebrew-tap-setup`).
- Dispatch payloads are `{"formula":"name","version":"1.2.3"}` and
  `{"cask":"name","version":"1.2.3"}`; `version` is optional.
- The tap name comes from the repository name without its `homebrew-` prefix:
  `owner/homebrew-tap` is `owner/tap`.

## Creating formulae and casks

`homebrew-add` starts every formula and cask from `brew create --tap
<owner>/<tap>`, so the tap must be tapped on the machine (`brew tap <owner>/<tap>
<path>`) and trusted (`brew trust --tap <owner>/<tap>`) when Homebrew asks. The tap
name is the `origin` remote without its `homebrew-` prefix. Nothing from the plugin
is installed into the tap.
