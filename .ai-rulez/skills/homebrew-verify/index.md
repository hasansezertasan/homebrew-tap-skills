# Concepts

* [Homebrew Verify](SKILL.md) - Decide whether a Homebrew tap change is verified and ready - run the read-only pre-PR readiness gate after adding, updating, repairing, or removing a formula or cask, and report the verdict with the evidence. Use for readiness verdicts and verification reports: brew audit, source build and test, livecheck, extras marker, placeholder casks, README catalog freshness and whether bottle or macOS install evidence is needed. It never edits formulae or casks; that is homebrew-fix-formula's job.
