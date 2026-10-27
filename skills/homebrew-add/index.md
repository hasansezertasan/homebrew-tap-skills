# Concepts

* [Homebrew Add](SKILL.md) - Use when adding a formula (PyPI Python CLI, or a source build such as Rust, Go, Node, CMake or autotools) or a cask (prebuilt macOS app or per-platform CLI binary archives from a GitHub release) to this Homebrew tap, including a project that ships both. Triggers include "add <package> as a formula", "add <repo> as a cask" and any request to package something in the tap. Start from `brew create --tap` and finish the skeleton by hand; never hand-write resource blocks and never run brew create without --tap.
