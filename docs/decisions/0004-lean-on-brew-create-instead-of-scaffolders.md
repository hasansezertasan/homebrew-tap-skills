# 0004: Lean on `brew create` instead of bundled scaffolders

Status: accepted; supersedes the scaffolder placement in [0001](0001-mirror-scoop-bucket-skills.md). Date: 2026-10-26.

`homebrew-add` shipped `add_formula.py` and `add_cask.py` (with `tap_name.py` and
`url_fetch.py`). A Rust scaffolder proposed in
[#26](https://github.com/hasansezertasan/homebrew-tap-skills/pull/26) drew four
review rounds, each re-implementing another part of Cargo's own rules, and was
closed. This record keeps why the other two went as well; it is not updated as the
project evolves.

## Decision

- **Start from `brew create --tap`, finish by hand.** It writes into the tap (never
  homebrew-core), downloads the artifact for its checksum, templates a cask's
  version into its URL and, for `--python`, resolves the whole resource tree with the
  same `PyPI.update_python_resources!` that `brew update-python-resources` runs in the
  tap's update workflows. It has templates for Rust, Go, Node, CMake, autotools and
  more.
- **What the scripts guarded becomes a checklist in the skill.** SPDX license,
  `desc` rules, `livecheck`, the extras comment, `.pkg` uninstall ids, cask token
  grammar, version templating, architecture handling and placeholder casks stay in
  `homebrew-add` as guidance, where an agent can adapt them to the project in front
  of it. `brew audit --strict` still catches what a checklist misses.
- **No script for what Homebrew already does.** A new script needs a reason Homebrew
  cannot meet. `homebrew-producer-dispatch`'s `bump_job.py` stays: it writes the
  dispatch payloads the tap's receivers read, and nothing in Homebrew does that.

## Checked

- `brew create --tap --python` on a PyPI sdist gave a complete formula that passed
  `brew audit --strict` once `desc`, `homepage`, `license`, `livecheck` and the test
  were filled in; `brew update-python-resources --package-name='pkg[extra]'` added
  extras-only resources.
- `brew create --tap` on Go, Rust, Node and autotools sources, and `--cask` on a
  release `.dmg`, produced the skeletons the skill describes.
- `brew bump-formula-pr` cannot edit `url` stanzas inside `on_macos`/`on_arm` blocks
  (`Could not find 'url' stanza!` on Homebrew 7.0.11), so no per-platform formula can
  be bumped by the tap's workflows. The skill routes those projects to a source
  build or a flat cask instead.

## Not checked

- Installing casks on Linux, and `brew bump-cask-pr` with Linux hash keys.
- A full `--build-from-source` install of a generated Python formula.

## Consequences

- The `# homebrew-tap:extras=` contract stays, now written by hand.
- Losing the scripts loses their unit tests and the `--check` convenience; run the
  `brew audit`, install and `brew test` commands the skill names, or `homebrew-verify`.
