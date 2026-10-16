# Installation

Your agent is the interface. Install the skills once, then ask your agent to set
up and operate a Homebrew tap; you do not run the individual commands yourself.

Copy this prompt into your coding agent:

```text
Install the homebrew-tap-skills skills: pick the best installation method for
you from https://github.com/hasansezertasan/homebrew-tap-skills/blob/main/docs/installation.md

Then use its homebrew-tap-setup skill to set up a new Homebrew tap from
https://github.com/hasansezertasan/copier-homebrew-tap. Ask me for what you need
(my GitHub owner, the tap's purpose and the first package), and ask before you
create a repository, change settings or secrets, or push.
```

The prompt points at this page, not at a command, so the routes below can change
without the prompt changing.

## Then use it

Each request below starts a skill. Say what you want in your own words.

| Ask your agent to | Skill |
| --- | --- |
| Set up a new tap from the template | `homebrew-tap-setup` |
| Add a formula (PyPI CLI) or a cask (macOS app) | `homebrew-add` |
| Repair livecheck, resources, checksums or cask stanzas | `homebrew-fix-formula` |
| Explain a failing scheduled or dispatch update | `homebrew-update-triage` |
| Retire a formula or cask and handle dependents | `homebrew-remove-or-deprecate` |
| Check a change is ready for a PR | `homebrew-verify` |

## Keep it current

| Ask your agent to | What happens |
| --- | --- |
| Update the homebrew-tap-skills skills | The agent runs the update command for the route it installed with (see the table below), then confirms the new version and tells you to start a new session. |
| Pull the latest template changes into this tap | The agent runs `uvx copier update` in the tap, reviews the diff and resolves conflicts with you. |

## For agents reading this page

You were pointed here to install the skills. Do this:

1. Pick the route in the table below that you can run yourself on your platform.
   Prefer a route native to your platform over a manual clone.
2. If a route needs a slash command or an interactive step you cannot run, give the
   user the exact command and ask them to run it. Do not guess at another command.
3. Confirm the install with the route's confirm step in the table.
4. Plugin and skills installs usually load in a new session, not in the
   conversation that installed them. If the skills are not available to you now,
   read `skills/homebrew-tap-setup/SKILL.md` from a clone of this repository (a
   temporary clone is fine) and follow it, and tell the user to start a new
   session so the installed skills load next time.
5. If a route fails, fall back to the manual route. Do not report the install as
   done until you have confirmed the skills or read `homebrew-tap-setup/SKILL.md`.
6. Then continue with what the user asked. Ask before you create a repository,
   change repository settings or secrets, or push. Do not install other agent
   skills or switch to a different route unless this one fails. The setup skill
   itself runs `uvx` (for Copier) and `mise` as it documents; that is expected.

### Routes

| Route | Install | Update | Confirm |
| --- | --- | --- | --- |
| Claude Code plugin | `claude plugin marketplace add hasansezertasan/homebrew-tap-skills`, then `claude plugin install homebrew-tap-skills@homebrew-tap-skills` (in a session: `/plugin marketplace add …` and `/plugin install …`) | `claude plugin marketplace update homebrew-tap-skills`, then `claude plugin update homebrew-tap-skills@homebrew-tap-skills` | `claude plugin list` shows the plugin and its version; run `/reload-plugins` or start a new session to load it |
| Codex plugin | clone this repository, then `codex plugin marketplace add /absolute/path/to/homebrew-tap-skills` and `codex plugin add homebrew-tap-skills@homebrew-tap-skills`; start a new thread | pull the clone, then reinstall from the local marketplace (`codex plugin add homebrew-tap-skills@homebrew-tap-skills`; `marketplace upgrade` applies to Git marketplaces, not a local path) and start a new thread | the plugin appears in Codex's plugin list in a new thread |
| A skills installer | `npx skills add hasansezertasan/homebrew-tap-skills -g` ([vercel-labs/skills](https://github.com/vercel-labs/skills); `-g` installs for the user so the skills are there in any project, add `-a <your agent>` to target one agent) | `npx skills update -g homebrew-tap-setup homebrew-add homebrew-fix-formula homebrew-update-triage homebrew-remove-or-deprecate homebrew-verify` (it filters by skill name, not repository name) | `npx skills list -g` shows the six skills |
| Manual | clone this repository and read `skills/<name>/SKILL.md`, or copy `skills/*` into your agent's skills directory | `git pull` in the clone, then copy `skills/*` again if you copied them | the clone's `git rev-parse HEAD` matches the latest commit on `main`; if you copied the skills, `diff -r <clone>/skills <destination>` prints nothing |

To compare an installed version with the latest, use the version in
`.claude-plugin/plugin.json` or the repository's latest GitHub release.

The Claude Code and Codex plugin routes each have one recorded installation
on macOS; the skills installer route has none: see
[host support](host-support.md) for the evidence per host. Treat the installer
route as unverified packaging guidance, and tell the user which route you used, whether
you confirmed the skills afterwards, and whether a new session is needed.

The skills assume a tap made from
[`copier-homebrew-tap`](https://github.com/hasansezertasan/copier-homebrew-tap)
and the layout in the [template contract](../.ai-rulez/references/contract.md).
