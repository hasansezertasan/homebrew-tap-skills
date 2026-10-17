---
type: Concept
title: Homebrew Tap Skills
x-ai-rulez:
  kind: context
  id: homebrew-tap-skills
---

This repository is a skills repository (root `skills/`) that also installs as a
Claude Code or Codex plugin, and is its own marketplace. It holds skills for
operating a Homebrew tap made from
[`copier-homebrew-tap`](https://github.com/hasansezertasan/copier-homebrew-tap).

#### Agent Instructions

`.ai-rulez/` is the single source for agent instructions and skills.
`AGENTS.md`, root `skills/`, `.claude-plugin/`, `.codex-plugin/`,
`.agents/plugins/marketplace.json`, and `.ai-rulez-generated.json` are
generated from it; edit `.ai-rulez/` and run `npm run generate`, then
commit the generated files. Never hand-edit generated files. Checks report
drift without repairing the checkout. Plugin identity, runtimes and the Codex
interface live in `.ai-rulez/config.toml`; it has no literal version, which
`package.json` supplies (see `CONTRIBUTING.md`).

#### Invariants

- The skills assume the layout in `.ai-rulez/references/contract.md`. Change a
  task name, path, or workflow filename there and in every skill that cites it,
  together.
- Skills read the tap's workflows and README for exact behavior instead of
  hardcoding flags; keep it that way. The scaffolders' own options are the one
  exception, because they ship here.
- Never scaffold with `brew create`: it writes into homebrew-core. Formulae and
  casks come from the `homebrew-add` scaffolders.
- Skills never edit `.gitignore` or other template-managed files by hand.
- Tap setup renders the Copier template (`homebrew-tap-setup`); it never
  hand-writes template-managed files.
- The `# homebrew-tap:extras=` comment the formula scaffolder writes is read by
  the tap's update workflows. Change both sides together.
- Maintainer governance stays in `AGENTS.md`, `CONTRIBUTING.md` and `docs/`;
  do not inject it into distributed skills.
- Keep host-loaded paths (`.mcp.json`, `hooks/`, `agents/`, `commands/`) out of
  the repository root: both catalogs install the root, and
  `scripts/check-repo.mjs` fails if one appears.
- Scope support claims to saved evidence; see `docs/host-support.md`.

#### Releases

Use Conventional Commit PR titles. release-please owns `CHANGELOG.md`, the
release manifest and the `package.json` version; the release workflow then
regenerates the plugin manifests on the release PR. Details in
`CONTRIBUTING.md`.

#### Commands

```sh
npm ci
npm run check
npm test
npm run generate
```
