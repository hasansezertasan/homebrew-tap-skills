# homebrew-tap-skills

Agent skills for operating a Homebrew tap: set one up, then add, fix, triage,
remove and verify formulae and casks. This is a skills repository
(`skills/<name>/SKILL.md`) that also installs as a Claude Code or Codex plugin.

| Skill | Use |
|---|---|
| `homebrew-tap-setup` | set up a new tap from the copier-homebrew-tap template |
| `homebrew-add` | add a PyPI formula or a prebuilt macOS app cask |
| `homebrew-fix-formula` | repair livecheck, resources, checksums, audit failures and cask stanzas |
| `homebrew-update-triage` | diagnose failing scheduled or dispatch updates |
| `homebrew-remove-or-deprecate` | retire formulae and casks and handle dependents |
| `homebrew-verify` | read-only pre-PR readiness gate |

The quickest way is to give your agent the prompt in
[docs/installation.md](docs/installation.md), which tells it to pick the best
install route for itself.

Install in Claude Code yourself, from inside the tap repository, at project
scope (the skills only apply to a tap):

```sh
claude plugin marketplace add hasansezertasan/homebrew-tap-skills
claude plugin install homebrew-tap-skills@homebrew-tap-skills --scope project
```

Install in Codex yourself, from a checkout:

```sh
codex plugin marketplace add /absolute/path/to/homebrew-tap-skills
codex plugin add homebrew-tap-skills@homebrew-tap-skills
```

Both install flows were run once on macOS (see [host support](docs/host-support.md)
for versions and scope); that is an install and one desk prompt, not a
task-success result. Other agents can read `skills/<name>/SKILL.md`. See
[host support](docs/host-support.md) for the evidence recorded per host. The
skills assume the layout in the
[template contract](.ai-rulez/references/contract.md).

The formula and cask scaffolders are part of `homebrew-add`
(`skills/homebrew-add/scripts/`); a tap does not need to carry its own.

## Development

Skills are authored in `.ai-rulez/`; root `skills/`, the plugin manifests and
`AGENTS.md` are generated and committed. See [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
npm ci
npm run generate
npm run check
npm test
```
