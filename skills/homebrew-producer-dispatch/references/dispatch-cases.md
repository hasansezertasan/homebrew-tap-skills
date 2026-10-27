# Producer Dispatch Evidence and Cases

## Provenance

The standard job was read, not run, from two producers of the same owner as they
stood on 2026-10-19: `hwid` (a formula, in `.github/workflows/release.yml`) and
`keycast` (a cask, which adds a `is_prerelease != 'true'` condition to the gate).
Both render `release.yml` from `copier-pyproject` (`.copier-answers.yml` names it
as the source, and the template's `include_homebrew` question enables the job).
The receivers are the template's `update-formula-dispatch.yml` and
`update-cask-dispatch.yml`. The cases below are synthetic desk scenarios grounded
in those files, not recorded runs against a real producer release.

The decision record is ADR 0003, `docs/decisions/0003-producer-dispatch-is-a-release-job.md`
in the repository that ships this skill.

## Local evidence map

| Evidence | Locator |
| --- | --- |
| The standard job (`needs`, `release_created` gate, `permissions: {}`, `gh api .../dispatches`, skip without the secret) | a producer's `.github/workflows/release.yml`, job `bump-homebrew` |
| Event types, payload keys and anchored validation | the tap's `update-formula-dispatch.yml` and `update-cask-dispatch.yml`, "Validate payload" |
| Token scope (Contents: write on the tap, no Pull requests) | the receivers' header comment; `homebrew-tap-setup`, credentials table |
| Template ownership of the job | the producer's `.copier-answers.yml` (`_src_path`) and the template's `include_homebrew` question |
| Rendering and classification | this skill's `scripts/bump_job.py` and `scripts/classify_producer.py`, tested in `tests/` |

## Known limits

- `classify_producer.py` is text matching over the workflows, not a YAML parser (the
  scripts are standard library only), so its answer is a first pass. It finds the
  job by its name (`bump-homebrew`, at any indent) and a dispatch by
  `repos/<tap>/dispatches`, or a `repository: <tap>` line in a `repository-dispatch`
  step. Whole-line comments are ignored; the tap matches whatever the case.
- It does not recognise a repository name built from variables or `vars`, a dispatch
  inside a reusable workflow or composite action, or YAML flow style. Those classify
  as `none`, so the skill confirms from the workflows before it writes a job.
- It counts jobs, not steps: two dispatch steps inside one `bump-homebrew` job count
  once. It matches the target and the event type separately within a job, so a job
  that sends `update-cask` to this tap and `update-formula` elsewhere reads as
  wired for either kind. `--kind` compares the event type of the job, not of each
  command.
- There is one `bump-homebrew` job per producer, so a producer's formula job and a
  wanted cask job are a collision, reported as `other-kind-job`.
- `bump_job.py` hardcodes the receivers' event types, payload keys and name pattern,
  because it ships here; the skill checks its output against the receivers.
- The script cannot tell whether a producer's release workflow is still shaped as
  the user described; the user supplies the job ids and expressions.
- If `copier-pyproject` changes its job, this skill's job has to change with it;
  they are kept in step by hand.
- No producer release has fired a dispatch produced by this skill.

## Cases

- **Producer already has the job.** `classify_producer.py` returns `standard-job`.
  Report it and stop; do not add a second job.
- **Producer rendered from copier-pyproject, `include_homebrew` off.** Result
  `template-owned`. Propose `copier update` with it enabled; do not hand-edit
  `release.yml`.
- **Name missing from the tap.** The receiver would reject it with "not found".
  Stop and hand off to `homebrew-add`.
- **Secret absent.** The job warns and skips, the producer still releases, and the
  tap never hears of it. Say so.
- **No version expression.** The payload carries only the name and the receiver's
  livecheck chooses the version.
