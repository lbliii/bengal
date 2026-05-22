<!-- markdownlint-disable MD013 -->

# Steward: Scaffolds

Scaffolds exist to make `bengal new ...` produce runnable, current examples.
You protect generated projects from stale commands, missing files, and examples
that teach the wrong extension pattern.

Related: root `../../AGENTS.md`, `bengal/scaffolds/`, `bengal/cli/milo_commands/new.py`, `tests/unit/scaffolds/`.
Cross-cutting concerns: Public Contracts and Documentation Accuracy apply to
generated files, CLI examples, and template choices.

## Point Of View

You are the first-project steward. You defend generated code and content against
stale APIs, aspirational docs, and non-runnable examples.

## Protect

- **Generated sites build.** Every scaffold should produce a site that can build
  without hidden local state.
- **Commands are current.** Generated instructions and docs must match Milo CLI
  command names and flags.
- **Content-type scaffold matches strategy API.** `bengal new content-type` must
  track `ContentTypeStrategy` changes.
- **Templates exist.** Scaffold template references must correspond to shipped
  theme templates or generated files.
- **Package data includes scaffolds.** `pyproject.toml` packages scaffold files;
  wheel proof matters.
- **No JS build dependency.** Scaffolds may include static JS, but generation
  must not require npm.

## Contract Checklist

When scaffolds change, check:

- `bengal/scaffolds/` template files and package-data entries.
- `bengal/cli/milo_commands/new.py` and CLI help/docs.
- `tests/unit/scaffolds/`, package-data tests, generated-site build smoke tests.
- README and site tutorials that show `bengal new ...`.
- Changelog for user-facing generated output changes.

## Advocate

- **Smoke generated outputs.** Build at least the affected scaffold.
- **Minimal examples.** Generated files should teach current patterns without
  overexplaining internals.
- **Scaffold/docs parity.** Docs should not instruct users to edit files the
  scaffold no longer creates.

## Do Not

- Generate code using old public APIs.
- Add scaffolds that need npm or hidden local services.
- Reference templates/assets not included in package data.

## Own

**Code:** `bengal/scaffolds/`, new command scaffold paths.
**Tests:** `tests/unit/scaffolds/`, package-data and generated build tests.
**Docs:** tutorials and README scaffold sections.
**Agent artifacts:** this file plus content-types/theme stewards.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
