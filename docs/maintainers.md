# Operating a Homebrew tap with these skills

The skills assume a tap made from
[`copier-homebrew-tap`](https://github.com/hasansezertasan/copier-homebrew-tap) and the
layout in the [template contract](../.ai-rulez/references/contract.md). Provide
the tap checkout and a concrete outcome.

| You want to | Start with |
| --- | --- |
| Set up a new tap from the template | `homebrew-tap-setup` |
| Add a formula (PyPI CLI) or a cask (macOS app) | `homebrew-add` |
| Repair livecheck, resources, checksums or cask stanzas | `homebrew-fix-formula` |
| Understand a failing scheduled or dispatch update | `homebrew-update-triage` |
| Make a package's releases update this tap | `homebrew-producer-dispatch` |
| Retire a formula or cask and handle dependents | `homebrew-remove-or-deprecate` |
| Decide whether a change is ready for a PR | `homebrew-verify` |

Every formula- or cask-changing skill finishes with `homebrew-verify`, the
read-only readiness gate. `homebrew-update-triage` diagnoses and delegates
repairs to `homebrew-fix-formula`; it does not redesign the update workflows.

Reports use `passed`, `pending` and `skipped` distinctly. A local gate does not
prove a formula builds or a cask installs; that evidence comes from the tap's
`tests.yml` run for the exact head SHA, or a local `brew audit`, source build and
`brew test`.

These skills do not change host permissions or authorize outward actions:
pushing, opening a PR, applying the `pr-pull` label or triggering a remote
workflow follows your own approval rules. Setup renders the template with Copier;
creating the repository and changing its settings or secrets follow the same
rules.
