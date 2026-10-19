# 0003: Producer dispatch is a release job, owned by the template where one exists

Status: accepted. Date: 2026-10-19.

The tap-side skills cover bumps, but nothing wires a producer to the tap's
`repository_dispatch` receivers ([issue #18](https://github.com/hasansezertasan/homebrew-tap-skills/issues/18)).
This record keeps why the `homebrew-producer-dispatch` skill is shaped as it is;
it is not updated as the project evolves.

## Decision

- **Runs in the tap, changes the producer.** Like every skill here it runs in
  the tap. The tap comes from `origin`, and the formula or cask name is checked
  against the local `Formula/` or `Casks/`. The change reaches the producer only
  as a pull request, from a fork when the user lacks write access. The skill
  asks before it pushes or posts.
- **The user supplies the producer.** The producer's GitHub URL, the package's
  registry name, formula or cask, the jobs to wait on and the version output are
  all given, never inferred. The skill does not assume PyPI.
- **The standard is a `bump-homebrew` job in the producer's release workflow.**
  `hwid` (formula) and `keycast` (cask) already carry it: `needs` on the release
  jobs, a `release_created` gate, `permissions: {}`, and
  `gh api repos/<tap>/dispatches` with `event_type=update-formula|update-cask`.
  It skips with a warning when the secret is absent. The skill writes this
  shape, and a producer that already has it is reported and left alone.
- **`copier-pyproject` owns the job where it is used.** Those producers render
  `release.yml` from the template (`include_homebrew`), whose answers file says
  never to edit it by hand. The skill proposes enabling `include_homebrew`
  through `copier update`; it edits `release.yml` directly only when there is no
  such answers file.
- **The skill never creates the token.** `HOMEBREW_TAP_TOKEN` is the default
  secret name and can be overridden. Its scope is the tap only, Contents: write.
  The skill checks the secret exists with `gh secret list`, states the scope in
  the pull request and the final report, and never sets or reads the value.

## Alternatives not taken

- **A separate dispatch workflow** (`workflow_run` on the publish workflow, with
  `peter-evans/repository-dispatch`), as the issue sketched. It duplicates the
  job producers already carry, would dispatch twice beside it, and fights the
  template that renders `release.yml`.
- **Appending a job to the release workflow by hand in template producers.** The
  next `copier update` would conflict with it or drop it.
- **Setting the secret from the skill.** It would put a credential value in the
  agent session and shell history for a step that is one command for the user.

## Consequences

- `contract.md` gains no section: the tap side is unchanged, and the skill
  reads the receivers' event types and payload keys instead of hardcoding them.
- `homebrew-tap-setup` is reworded so `HOMEBREW_TAP_TOKEN` reads as the
  producer-side secret this skill owns.
- If `copier-pyproject` changes the job, the skill's standard shape has to change
  with it; the two are kept in step by hand.
