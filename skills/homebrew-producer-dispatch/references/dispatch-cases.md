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

- `classify_producer.py` finds the job by its name (`bump-homebrew`) and a dispatch
  by `repos/<tap>/dispatches` or a `repository: <tap>` line. A workflow that builds
  the repository name from variables is not recognised and classifies as `none`.
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
