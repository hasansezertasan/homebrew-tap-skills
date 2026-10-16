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

Install in Claude Code yourself:

```sh
/plugin marketplace add hasansezertasan/homebrew-tap-skills
/plugin install homebrew-tap-skills@homebrew-tap-skills
```

Install in Codex yourself, from a checkout:

```sh
codex plugin marketplace add /absolute/path/to/homebrew-tap-skills
codex plugin add homebrew-tap-skills@homebrew-tap-skills
```

These install flows follow the plugin manifests, but a successful installation
has not yet been recorded for Claude Code or Codex, so treat them as unverified
packaging guidance. Other agents can read `skills/<name>/SKILL.md`. See
[host support](docs/host-support.md) for the evidence recorded per host. The
skills assume the layout in the
[template contract](.ai-rulez/references/contract.md).

The formula and cask scaffolders ship inside `homebrew-add`
(`skills/homebrew-add/scripts/`); the tap itself no longer carries them.

## Development

Skills are authored in `.ai-rulez/`; root `skills/`, the plugin manifests and
`AGENTS.md` are generated and committed. See [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
mise install
mise run agents:generate
mise run check
```
