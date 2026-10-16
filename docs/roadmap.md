# Roadmap

Work that is planned or open, but not yet done. Decisions already taken are in
[docs/decisions](decisions/). Remove an item once it ships and link its
evidence from the relevant guide.

## Evidence gaps

- **Model trials.** The eval cases in each skill's `evals/` are desk exercises
  with rubrics. None has been run against a model yet, so no skill is shown to
  pass its cases. Run `ai-rulez eval run` (the activation ranking is offline and
  informational) and record the runner, model, run count and cost before making
  any claim. Authenticated model evaluations stay out of CI.
- **Host installs and skill use.** [Host support](host-support.md) records no
  successful plugin installation and no skill-use run for any host.
- **Real taps.** No skill has run against a real tap. The workflow-derived
  examples in each `references/` file are not recorded `brew` runs. Needs macOS
  with Homebrew and a tap made from the template.
- **Template version.** The contract names `copier-homebrew-tap` 0.1.0 as the
  minimum template version, but that template has no release yet. Recheck every
  locator against the first tagged release.
- **Adoption of existing taps.** `homebrew-tap-setup` describes adopting the
  template in a tap that has no `.copier-answers.yml`; that path has not been
  exercised on a real tap.
