---
type: Playbook
title: Homebrew Tap Setup
description: Set up a new Homebrew tap by rendering copier-homebrew-tap with Copier, then configure repository naming (homebrew-<tap>), Actions settings, the producer dispatch token and bottle publishing through the pr-pull label, and hand the first formula or cask to homebrew-add and homebrew-verify. Use for new-tap bootstrap, for adopting the template in an existing tap, and for questions about copier copy or update, or why update PRs get no bottles unless the optional `WORKFLOW_TOKEN` is set.
x-ai-rulez:
  kind: skill
  id: homebrew-tap-setup
  metadata:
    name: homebrew-tap-setup
---

# Set Up a Homebrew Tap from the Template

Read the [template contract](../../references/contract.md) for the task names and paths
this skill relies on.

## 1. Establish the destination and outcome

Confirm the intended `owner/homebrew-<tap>` repository, visibility, default
branch, local directory, and the first package and its kind (formula or cask).
Ask through the native question tool when these are unspecified or disagree; do
not invent an owner or a demo package. Distinguish a setup plan, a local render
and a published installable tap. Follow the user's approval rules for creating
repositories, changing settings or secrets, pushing, opening PRs and running
remote workflows.

Homebrew requires a third-party tap repository to be named `homebrew-<tap>`:
`brew tap <owner>/<tap>` resolves to `<owner>/homebrew-<tap>`, and `homebrew-tap`
is the usual choice. A repository without the prefix cannot be tapped by its
short name. Do not suggest dropping it.

Read the template's `copier.yml` for the current questions and defaults, and the
rendered tap's `README.md`, `AGENTS.md`, `.github/workflows/` and
`.config/mise.toml`, instead of relying on this skill's summary of them. Use
[references/setup-cases.md](references/setup-cases.md) for evidence and worked
cases; recheck its locators after the template changes. Do not redesign
workflows, token plumbing or template files as an implicit setup step. Surface
unsupported choices and agree their scope first.

## 2. Render the template

Render into a new directory with Copier; the template is not a GitHub template
repository, so "Use this template" and `gh repo create --template` do not apply.
Provide the answers from step 1 with `-d name=value` so the run is reproducible,
or answer the prompts; `copier.yml` is the source for question names and
defaults. Pin the template version with `--vcs-ref` when the user asks for one.

```sh
uvx copier@9.19.1 copy gh:hasansezertasan/copier-homebrew-tap <directory>
```

Copier renders files only. Creating the GitHub repository, `git init`, the
`origin` remote, the first commit and the push are separate steps that follow the
user's approval rules. Settings, secrets, labels, rulesets, required checks and
installed apps (Renovate, for example) are not rendered; check each separately.

Commit `.copier-answers.yml`, and never edit it by hand: `copier update` reads it
to merge later template changes. Files the template manages come from it; change
them through `copier update` (or an agreed template change), not by editing them
to diverge. `.gitignore` is Cobo-managed; use Cobo's sync if `mise run check`
reports drift.

Answers only feed the README install snippet and the LICENSE copyright line.
Scripts and workflows read the tap identity at run time from the Git remote and
the Actions context. Check the rendered `README.md` title and description and
`LICENSE` against the agreed identity. Do not globally replace owner names:
external actions and dependencies are not tap identity.

### Adopting the template in an existing tap

A tap created from the old GitHub template repository has no
`.copier-answers.yml`, so `copier update` cannot work on it. Do not overwrite the
tap blindly. Render the template into a scratch directory with answers matching
the tap, compare it with the tap file by file, and bring over only changes the
user approves, keeping the tap's formulae, casks, history and README prose. Then
add the rendered `.copier-answers.yml` so later updates work. Treat this as a
separate, reviewed change.

## 3. Configure Actions and credentials from actual consumers

In **Settings → Actions → General**, verify Actions is enabled and policy allows
the pinned actions the rendered workflows use. Keep the default workflow
permissions read-only: every workflow sets `permissions: {}` and each job grants
itself what it needs, so the repository default does not apply to them. Tick
**Allow GitHub Actions to create and approve pull requests**, which the update
workflows need to open PRs. Do not broaden defaults or jobs to troubleshoot;
inspect effective job permissions and repository policy instead.

Explain the distinct credentials before requesting any secret:

| Consumer | Credential and access |
| --- | --- |
| Weekly livecheck updates, dispatch receivers and the Cobo drift sync (branch push and PR creation) | Built-in `GITHUB_TOKEN` by default. These workflows read the optional repository secret `WORKFLOW_TOKEN` first and fall back to `GITHUB_TOKEN`; no workflow reads `HOMEBREW_TAP_TOKEN`. |
| `brew pr-pull` (`publish.yml`) | Built-in `GITHUB_TOKEN` with Contents, Pull requests and Actions/Checks/Issues read as the workflow declares; it pushes the bottle commit to `main`. |
| Dispatch failure issue (`update-cask-dispatch.yml`) | Built-in `GITHUB_TOKEN` with Issues: write; the destination is `github.repository`. |
| PR title and branch-name lint | Built-in `GITHUB_TOKEN` with Pull requests: write. |
| External producer repository calling `POST /repos/<owner>/<repo>/dispatches` | A fine-grained token scoped to the tap with Contents: write. Store it in the producer repository, not in the tap. |

`GITHUB_TOKEN` is supplied by Actions, not a secret the user creates. The
producer-side secret is `HOMEBREW_TAP_TOKEN`, written into a producer's release
workflow by `homebrew-producer-dispatch`; it belongs in the producer, and no
workflow in the tap consumes it. Do not invent an alias or edit tap workflows to
read it without agreed scope.

Explain what `GITHUB_TOKEN` costs. A PR opened with it does not trigger
`tests.yml`, so update PRs carry no bottle build. The bump jobs therefore audit,
build from source and test a formula bump inside the run that opens the PR; casks
are audited. Bottles come later: close and reopen the PR or push to its branch to
run `tests.yml`, and only after that apply the `pr-pull` label. The same applies
to the Cobo drift PR. The optional `WORKFLOW_TOKEN` removes that manual step:
offer it, never require it. Recommend a fine-grained token scoped to the tap with
Contents and Pull requests write, or a GitHub App token, and agree its expiry and
renewal first; do not recommend blanket `repo`, admin or Actions-write
privileges.

Configure secrets through Settings → Secrets and variables → Actions or secure
CLI input. Never print values, ask for them in chat, commit them or embed them in
shell source. Enable Issues if dispatch failure reporting is wanted. Create the
`pr-pull` label if it does not exist, and report policy or ruleset blockers
rather than escalating privileges speculatively.

## 4. Prepare the first formula or cask

Run `mise install` in the rendered tap. Invoke `homebrew-add` to select and
scaffold the first item; do not hand-write Ruby or invent a demo package.
`homebrew-add` delegates its gate to `homebrew-verify`. Take PR scope and
branch conventions from the tap's own instructions.

Bottle publishing follows Homebrew's `brew test-bot` flow, documented in the
rendered README: CI builds bottles on the PR, then applying the `pr-pull` label
runs `publish.yml`, which pulls the bottle commits and pushes to `main` (see the
template's `publish.yml` for the exact permissions). The first formula therefore
needs a maintainer to apply the label; casks do not use bottles. Confirm
`pull_request_target` runs from the default branch, so `publish.yml` must already
be merged there.

The workflows filter on `main`. Confirm the default branch before relying on
that; a different default branch needs every branch filter inspected and an agreed
adaptation, not a claim of support.

## 5. Report readiness at the requested level

Use the [setup report](references/setup-report.md) as a guide. Report the
destination and default branch, the template version recorded in
`.copier-answers.yml`, checkout identity, rendered versus separately configured
items, credential **names and purposes only**, the first item's kind, local
checks and the `homebrew-verify` verdict. Include owner-neutral consumer
commands with the established values:

```sh
brew tap <owner>/<tap>
brew install <owner>/<tap>/<formula>
brew install --cask <owner>/<tap>/<cask>
```

Keep `passed`, `pending` and `skipped` distinct. An empty tap, or a weekly
update run with `dry_run`, does not exercise install, bottle publication or PR
creation. Schedules and `repository_dispatch` run only from workflows on the
default branch; check actual runs before claiming automation works. Hand update
failures to `homebrew-update-triage` and formula repair to `homebrew-fix-formula`.
