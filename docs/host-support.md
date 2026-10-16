# Host support

The skills are generated into root `skills/` from `.ai-rulez/`. Claude Code
and Codex have catalogs that install the repository root (`./`). OpenCode
does not scan root `skills/`; the root `opencode.json` points it there.

| Host | Packaging | Evidence recorded |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `ai-rulez verify --plugin` (hash check of generated files) only; no installation or skill use recorded |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` | `ai-rulez verify --plugin` only; no installation or skill use recorded |
| OpenCode | `opencode.json` (`skills.paths`) | Not evaluated |
| pi | none declared (no pi package or path configured) | Not evaluated |
| Other agents | `AGENTS.md` | Not evaluated |

Structural validation and completed model turns do not establish task success
by themselves. Add a row's evidence only after recording it (command, host
version, date). Authenticated model evaluations stay out of ordinary CI.

## Install

```sh
/plugin marketplace add hasansezertasan/homebrew-tap-skills
/plugin install homebrew-tap-skills@homebrew-tap-skills
```

For Codex, from a checkout:

```sh
codex plugin marketplace add /absolute/path/to/homebrew-tap-skills
codex plugin add homebrew-tap-skills@homebrew-tap-skills
```
