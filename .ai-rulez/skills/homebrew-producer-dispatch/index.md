# Concepts

* [Homebrew Producer Dispatch](SKILL.md) - Connect a package's own repository (the producer) to this tap by opening a pull request on the producer that adds the release hook. Run from the tap. Use when wiring a new producer, adding the producer-side `HOMEBREW_TAP_TOKEN` secret, or enabling `include_homebrew` in a copier-pyproject producer. Not for diagnosing or repairing the tap itself.
