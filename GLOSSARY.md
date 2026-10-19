# Homebrew tap skills

Language for operating a Homebrew tap and wiring the packages that feed it.

## Language

**Tap**:
A GitHub repository named `homebrew-<tap>` that holds formulae and casks, made from `copier-homebrew-tap`. The skills run here.
_Avoid_: Bucket, repo (unqualified)

**Producer**:
The repository that builds and releases a package a tap distributes. It signals the tap after a release and never edits the tap.
_Avoid_: Source repo, package repo, upstream

**Receiver**:
The tap's `repository_dispatch` workflow that bumps a formula or cask when a producer signals.
_Avoid_: Listener, handler

**Dispatch**:
The cross-repository signal a producer sends to its tap's receiver after a release, carrying the formula or cask name and, optionally, the version.
_Avoid_: Trigger, webhook, ping

**Bump job**:
The `bump-homebrew` job in a producer's release workflow that sends the dispatch. It is the standard shape, and a producer rendered from `copier-pyproject` gets it from the template.
_Avoid_: Dispatch workflow, release hook

**Tap token**:
The producer's `HOMEBREW_TAP_TOKEN` secret: a credential scoped to the tap with Contents: write, used only to send the dispatch.
_Avoid_: PAT, `WORKFLOW_TOKEN` (a different, tap-side secret)
