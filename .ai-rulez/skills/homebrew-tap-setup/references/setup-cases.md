# Tap Setup Evidence and Cases

## Provenance

Inspected the Copier conversion of `copier-homebrew-tap` (renamed from
`tap-template`) as it stood before its first release. No tag exists yet, so the
contract's minimum template version, `v0.1.0`, is the first release that will
include the conversion. Recheck every locator against the first tagged release
before relying on this file. Locators are paths in that repository; files under
`template/` land at the same path without the prefix in a rendered tap. The cases
are synthetic desk scenarios grounded in the workflows, not observed failed
setups or recorded `brew` runs.

Read the verification, repair, triage and lifecycle references for their separate
evidence boundaries. A Cobo drift failure is a managed boilerplate failure, not
proof of a template, token or formula incident.

## Local evidence map

| Evidence | Locator |
| --- | --- |
| Questions, defaults, template root, post-copy message | `copier.yml` |
| Rendered answers record used by `copier update` | `template/.copier-answers.yml.jinja` |
| What the rendered setup checklist says (read-only default permissions, PR-creation setting) | `template/README.md.jinja`, Setup / Automated updates |
| Tap name derivation (`owner/homebrew-x` to `owner/x`) | each workflow's `${repository#homebrew-}` step |
| Token use and PR creation | `template/.github/workflows/update-formulas.yml`, `update-casks.yml`, `update-formula-dispatch.yml`, `update-cask-dispatch.yml` (`token: ${{ secrets.GITHUB_TOKEN }}`) |
| Dispatch payloads and anchored validation | `update-formula-dispatch.yml` and `update-cask-dispatch.yml`, "Validate payload" |
| Failure issue | `update-cask-dispatch.yml`, "Report failure" (Issues: write) |
| Bottle build and tap-syntax gate | `template/.github/workflows/tests.yml`, `syntax`, `formulae` and `cask-audit` jobs |
| Bottle publication | `template/.github/workflows/publish.yml` (`pull_request_target`, label `pr-pull`) |
| Adding the first item and verification ownership | the `homebrew-add` and `homebrew-verify` skills |
| Local check coverage | `template/.config/mise.toml`, `check` |
| PR title and branch-name lint | `template/.github/workflows/check-pr-title.yml`, `check-branch-name.yml` |
| Template renders and its own gate passes | `.github/workflows/template.yml` |

Recheck code rather than treating comments as authoritative. All workflows deny
permissions by default and each job opts in: update PR jobs need Contents and
Pull requests write, `publish.yml` needs Contents write, the dispatch cask failure
report needs Issues write, and the lints need Pull requests write. Do not
generalize one job's permissions to every workflow.

## Short cases

| Case | Handling |
| --- | --- |
| User names the repository without the prefix, e.g. `mytap` | Explain that Homebrew resolves `brew tap owner/tap` to `owner/homebrew-tap`; a repository named `mytap` cannot be tapped by its short name. Agree a `homebrew-` name before rendering. |
| User asks for a `WORKFLOW_TOKEN` or `HOMEBREW_TAP_TOKEN` secret "so updates work" | No tap workflow reads either. Updates use `GITHUB_TOKEN`; only a producer dispatching to the tap needs a token, stored in the producer. |
| Update PRs have no bottles | Expected: a PR opened with `GITHUB_TOKEN` does not trigger `tests.yml`. Close and reopen the PR, then label `pr-pull` once bottles are built. |
| Existing tap with no `.copier-answers.yml` | It predates the Copier template; follow "Adopting the template in an existing tap" and do not run `copier update`. |
| Default branch is not `main` | Workflow filters and `publish.yml` target `main`; report it and agree an adaptation separately. |
| Empty tap passes `mise run check` | The gate runs with no formula or cask, so it proves the template renders, not that a package builds or installs. |

## Worked desk scenarios

Synthetic situations to evaluate decisions, not claims about published taps or
recorded `brew` runs.

### A. Unspecified destination and first package

Ask for owner and repository (with the `homebrew-` prefix), visibility, default
branch, the first upstream and route (PyPI formula or macOS cask), and whether
the goal is a plan or a published, verified tap. Render with `copier copy` and
explicit `-d name=value` answers. Distinguish rendered files from Actions
settings, secrets and branch policy, which the template does not configure. Keep
identity neutral and continue with `homebrew-add` then `homebrew-verify`; do not
invent a formula.

### B. Remote name that gives no usable tap name

The tap name `brew create --tap` and `brew tap` take is the `origin` remote without
its `homebrew-` prefix (`owner/homebrew-tap` is `owner/tap`). A remote without the
prefix gives `owner/repo`, a name `brew tap` cannot resolve, and a name copied from
another tap or an earlier session may point at the wrong owner. Check the remote
before trusting a tap name. A successful `brew create` does not prove the tap is
installable: that needs the files pushed and a `brew tap` plus install from the
remote, which a local run does not show.

### C. Wrong secret and an empty-tap check

Explain that no tap workflow reads `WORKFLOW_TOKEN` or `HOMEBREW_TAP_TOKEN`;
updates use `GITHUB_TOKEN`, and only a producer dispatching to the tap needs its
own token, stored in the producer. Cover the PR-creation setting and why a PR
opened with `GITHUB_TOKEN` starts no `tests.yml` run. An empty tap passing
`mise run check` proves the template renders, not that publishing, bottle
building or a cask install works. Never expose secrets or recommend blanket
privileges to hide missing evidence.

### D. Edited template-managed file, then `copier update`

A tap owner hand-edited a workflow the template manages and later wants
template fixes. Read `.copier-answers.yml` for the recorded source and version,
run `copier update` (with approval for the working tree) and resolve conflicts
deliberately. Do not delete the answers file or re-run `copier copy` over the
checkout. Resolve a managed-boilerplate drift failure through the managed sync,
not by hand-editing `.gitignore`.

## External documentation checked

Recheck current docs and destination policy during setup.

- [Copier](https://copier.readthedocs.io): `copier copy` renders files and
  records answers in `.copier-answers.yml`; `copier update` merges later template
  changes using that file.
- [Homebrew: How to create and maintain a tap](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap):
  a third-party tap repository is named `homebrew-<tap>`.
- [Homebrew brew test-bot and pr-pull](https://docs.brew.sh/Brew-Test-Bot-For-Core-Contributors):
  bottle build and publication flow the tap's workflows follow.
- [Actions repository settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository):
  workflow permissions and the PR-creation setting.
- [GITHUB_TOKEN and triggered workflows](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication):
  events created with the built-in token do not start new workflow runs.
