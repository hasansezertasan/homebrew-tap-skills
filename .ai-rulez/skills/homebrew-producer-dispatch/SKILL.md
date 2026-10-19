---
type: Playbook
title: Homebrew Producer Dispatch
description: Connect a package's own repository (the producer) to this tap by opening a pull request on the producer that adds the release hook. Run from the tap. Use when wiring a new producer, adding the producer-side `HOMEBREW_TAP_TOKEN` secret, or enabling `include_homebrew` in a copier-pyproject producer. Not for diagnosing or repairing the tap itself.
x-ai-rulez:
  kind: skill
  id: homebrew-producer-dispatch
  metadata:
    name: homebrew-producer-dispatch
---

# Wire a producer to the tap

Read the [template contract](../../references/contract.md) for the paths and the
dispatch payloads this skill relies on. It runs in the tap and changes the
producer only through a pull request; it never edits the tap.

## Establish the facts

Read `AGENTS.md` and the two dispatch receivers, `update-formula-dispatch.yml`
and `update-cask-dispatch.yml`, in the tap. Take the event types, the payload keys
and the validation patterns from them instead of from this skill. Derive the tap
repository, `owner/homebrew-<tap>`, from the `origin` remote or an explicit
override. The dispatch endpoint needs that full repository name, so do not use the
short `owner/<tap>` name `tap_name.py` prints.

Ask the user for each of these; infer none of them, and do not assume PyPI:

- the producer's GitHub URL;
- the package's registry name, and whether it ships as a formula or a cask;
- the producer's release workflow and the job ids the dispatch must wait on
  (`needs:`), which are the jobs that publish and release;
- the `if` expression that means "a release was created" (and, for a cask, "not a
  prerelease" if the producer has prereleases);
- the expression holding the released version, or that there is none.

Check the name exists in this tap: `Formula/<name>.rb` or `Casks/<name>.rb`. The
receiver rejects a name it cannot find, so stop and hand the user to
`homebrew-add` if it is missing.

## Look at the producer

Clone the producer into a fresh temporary directory and read its workflows there;
do not use the GitHub API or web pages to discover its files. Classify it:

```sh
python scripts/classify_producer.py "$PRODUCER_DIR" --tap "$TAP_REPO"
```

| Result | Meaning | Action |
| --- | --- | --- |
| `standard-job` | A workflow already has the `bump-homebrew` job. | Report it and stop. Show how it differs from the standard job only if asked; do not rewrite it. |
| `other-dispatch` | A workflow dispatches to this tap by other means. | Report which workflow and stop. Change or replace it only when the user asks, and never add a second dispatch beside it: each dispatch opens its own tap PR. |
| `template-owned` | No dispatch, and `.copier-answers.yml` shows the producer is rendered from `copier-pyproject`. | Do not hand-edit `release.yml`; the template renders it. Propose enabling `include_homebrew` through `copier update` in the producer's own clone (see below). |
| `none` | No dispatch and no template. | Add the standard job to the release workflow the user named. |

## The standard job

Render it with the script; do not hand-write it, so every producer carries the
same job. The values come from the user's answers above.

```sh
python scripts/bump_job.py formula hwid --tap "$TAP_REPO" \
  --needs release-please,finalize-release \
  --gate "needs.release-please.outputs.release_created == 'true'" \
  --version-expr "needs.release-please.outputs.version"
```

Use `cask` for a cask. Omit `--version-expr` when the producer has no version
expression; the payload then carries only the name and the receiver's livecheck
decides. Insert the printed job under `jobs:` of the release workflow, then compare
the edited workflow with the producer's other jobs for indentation, and run
`actionlint` or `zizmor` there if installed. The job has `permissions: {}`, reads
the secret only in its own step, and warns and skips when the secret is absent, so
a producer without the token still releases.

For a `template-owned` producer, run `copier update` with `include_homebrew` set
to true in a disposable branch of the clone, review the whole diff with the user
(a template update brings other changes too), and keep to the template's own
update recipe. If the template's job differs from the standard one, say so and
keep the template's.

## The token

The producer needs its own credential, because its built-in `GITHUB_TOKEN` cannot
post to another repository. State it, never create it:

- name: `HOMEBREW_TAP_TOKEN`, unless the user names another (then pass that name
  through to the job and say it differs from the template's);
- scope: a fine-grained token limited to the tap repository with **Contents:
  write** only;
- location: an Actions secret in the producer repository.

Never set the secret, read its value, or ask the user to paste it into the session.
Check whether it exists with `gh secret list -R "$PRODUCER"`, which lists names
only. State in the pull request and in the report that releases skip the bump
until it exists.

## Deliver as a pull request

Always a pull request, never a direct push to the producer's default branch. Use a
Conventional Branch name (`chore/homebrew-dispatch`) and a Conventional Commit
title (`chore: dispatch Homebrew updates to <tap>`). Push from a fork when the user
has no write access to the producer.

Pushing a branch and opening the pull request publish to another repository. Show
the user the diff and the drafted title and body, and ask for approval for each of
those two actions with the question tool. The body names the tap, the formula or
cask, the trigger and version expression, the token name and scope, and the
behavior without the secret.

## Finish

Hand the first real bump to `homebrew-update-triage` if the receiver rejects the
dispatch, and to `homebrew-verify` for the resulting tap PR. Use the
[dispatch report](references/dispatch-report.md) as a guide. Report `passed`,
`pending` and `skipped` separately: the dispatch is `pending` until a release fires
it, because nothing here has run against a real producer release. Read
[dispatch evidence](references/dispatch-cases.md) for the provenance of the shape
and its known limits, and label desk evaluations honestly.
