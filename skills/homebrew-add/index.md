# Concepts

* [Homebrew Add](SKILL.md) - Use when adding a formula (PyPI Python CLI or Rust CLI built with cargo) or a cask (prebuilt macOS app from a GitHub release) to this Homebrew tap, including a project that ships both. Triggers include "add <package> as a formula", "add <repo> as a cask" and any request to package something in the tap. Always scaffold with the bundled scripts; never hand-write resource blocks and never use brew create.
