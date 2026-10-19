# Roadmap

Work that is planned or open, but not yet done. Decisions already taken are in
[docs/decisions](decisions/). Remove an item once it ships and link its
evidence from the relevant guide.

## Evidence gaps

- **Model trials.** The eval cases in each skill's `evals/` are desk exercises
  with rubrics. One partial run exists: on 2026-10-16 `ai-rulez eval run
  homebrew-verify --runs 1 --no-write --model sonnet` (`claude-plugin-eval`
  runner, `--trust-plugin`) passed its 3 cases at about $0.14. That is one run of
  one skill, so the other five skills are not shown to pass their cases and this
  one is not a stable result. Run `ai-rulez eval run` for the rest (the
  activation ranking is offline and informational) and record the runner, model,
  run count and cost before making any claim. Authenticated model evaluations
  stay out of CI. Also open: the runner builds its temporary plugin copy as
  `skills/<name>/`, so a skill's `../../references/contract.md` link points at
  `references/` beside `skills/`, which the copy does not appear to contain. The
  transcripts show the contract was never read in that run. The generated root
  skills link `references/contract.md`, which exists, so installed plugins are
  not affected; only eval runs lack the contract. The copy was removed after the
  run, so this is inferred from the layout and the missing read, not inspected.
  `--runner-arg --trust-plugin` is required without a terminal and
  `--runner-arg --keep-temp` keeps transcripts.
- **Host installs and skill use.** [Host support](host-support.md) records the
  plugin installing on Claude Code and Codex (macOS) and one skill answering a
  desk prompt on each. That is one prompt and one run per host: no pass rate,
  and no skill has run against a real tap. OpenCode, pi and other agents are not
  evaluated.
- **Real taps.** No skill has run against a real tap. The workflow-derived
  examples in each `references/` file are not recorded `brew` runs. Needs macOS
  with Homebrew and a tap made from the template.
- **Template version.** The contract names `copier-homebrew-tap` 0.1.0 as the
  minimum template version, but that template has no release yet. Recheck every
  locator against the first tagged release.
- **Adoption of existing taps.** `homebrew-tap-setup` describes adopting the
  template in a tap that has no `.copier-answers.yml`; that path has not been
  exercised on a real tap.
- **Producer dispatch.** `homebrew-producer-dispatch` renders the same
  `bump-homebrew` job `hwid` and `keycast` carry, and its scripts are unit tested,
  but no producer release has fired a dispatch it produced and no producer pull
  request has been opened with it. Its eval cases are desk exercises that have not
  been run through `ai-rulez eval run`.
