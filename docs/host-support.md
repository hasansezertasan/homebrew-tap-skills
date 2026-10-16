# Host support

The skills are generated into root `skills/` from `.ai-rulez/`. Claude Code
and Codex have catalogs that install the repository root (`./`). OpenCode
does not scan root `skills/`; the root `opencode.json` points it there.

| Host | Packaging | Evidence recorded |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | `ai-rulez verify --plugin` (hash check of generated files); 2026-10-16, Claude Code 2.1.300, macOS: `claude plugin marketplace add hasansezertasan/homebrew-tap-skills` then `claude plugin install homebrew-tap-skills@homebrew-tap-skills` installed 0.1.0 (user scope, enabled) with all six skills present in the cache. Skill use, same day: `claude -p "$CLAUDE_PROMPT" --output-format stream-json --verbose --max-budget-usd 1` in an empty directory invoked `homebrew-tap-skills:homebrew-update-triage` through the Skill tool and answered from it (about $0.12); one prompt, one run, not a task-success result |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` | `ai-rulez verify --plugin`; 2026-10-16, codex-cli 0.162.1, macOS: `codex plugin marketplace add <checkout of main at 2ce096b>` then `codex plugin add homebrew-tap-skills@homebrew-tap-skills` installed 0.1.0 (enabled) with all six skills present in the cache. Skill use, same day: `codex exec --skip-git-repo-check --json "$CODEX_PROMPT" < /dev/null` in an empty directory (the prompt is a positional argument; `< /dev/null` only stops codex waiting on stdin) read the installed `homebrew-update-triage/SKILL.md` and its references and answered from them; one prompt, one run, not a task-success result |
| OpenCode | `opencode.json` (`skills.paths`) | Not evaluated |
| pi | none declared (no pi package or path configured) | Not evaluated |
| Other agents | `AGENTS.md` | Not evaluated |

Structural validation and completed model turns do not establish task success
by themselves. Add a row's evidence only after recording it (command, host
version, date). Authenticated model evaluations stay out of ordinary CI.

### Skill-use prompts

The exact prompts behind the 2026-10-16 skill-use rows (`$CLAUDE_PROMPT` and
`$CODEX_PROMPT`). They differ only in the last clause. No trace is saved in the
repository. Both plugins were uninstalled afterwards.

```text
The scheduled update-formulas workflow opened a PR with several updated formulae, but tests.yml never ran on it. How do I triage it? Desk exercise: do not edit anything, run installs, or use the network; no checkout is available, answer from the skill's guidance in a few lines.
```

```text
The scheduled update-formulas workflow opened a PR with several updated formulae, but tests.yml never ran on it. How do I triage it? Desk exercise: do not edit anything, run installs, or use the network; no checkout is available, answer from the homebrew-update-triage skill's guidance in a few lines.
```

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
