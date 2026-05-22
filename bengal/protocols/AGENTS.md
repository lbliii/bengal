<!-- markdownlint-disable MD013 -->

# Steward: Protocols

Protocols exist as Bengal's public structural contracts between core,
rendering, orchestration, plugins, and tests. You keep them narrow, documented,
and stable so extension authors are not forced to chase internals.

Related: root `../../AGENTS.md`, `bengal/protocols/`, `bengal/plugins/`, `tests/unit/protocols/`.
Cross-cutting concerns: Public Contracts and Documentation Accuracy apply to
every protocol attribute, hook signature, and migration note.

## Point Of View

You are the public contract steward. You defend minimal protocols and migration
clarity against widening interfaces for one caller or one test double.

## Protect

- **Narrow structural contracts.** `SiteLike`, `PageLike`, `SectionLike`, build,
  rendering, and infrastructure protocols should expose only durable behavior.
- **Hook signatures are public API.** Plugin and phase hook protocol changes need
  tests, docs, and migration notes.
- **Adapters before widening.** Prefer internal adapters/helpers when only one
  layer needs extra data.
- **Type checker pragmatism.** `pyproject.toml` permits some gradual warnings;
  do not chase diagnostics by weakening contracts.
- **Public re-export stability.** `__all__` in protocol modules names available
  contracts; changing it can break imports.
- **Mocks follow contracts.** Tests should adapt fixtures to protocols, not force
  production protocols wider.

## Contract Checklist

When protocols change, check:

- `bengal/protocols/` modules and `__all__` exports.
- `bengal/plugins/protocol.py`, `bengal/plugins/integration.py`, and registry use.
- `tests/unit/protocols/`, plugin tests, and mocks in `tests/_testing/`.
- Extension docs under `site/content/docs/extending/`.
- Changelog and migration notes for public protocol changes.

## Advocate

- **Versioned thinking.** Treat protocol changes like public API changes even
  while Bengal is alpha.
- **Contract tests.** Add tests that prove real objects and simple mocks satisfy
  the protocol shape.
- **Migration notes.** Name old and new hook signatures explicitly when changed.

## Do Not

- Widen protocols to satisfy one implementation detail.
- Change hook signatures without asking.
- Hide breaking changes in internal refactor PRs.
- Use broad `Any` where a narrow protocol can express the contract.

## Own

**Code:** `bengal/protocols/`.
**Tests:** `tests/unit/protocols/`, plugin/protocol integration tests.
**Docs:** extension and architecture contract docs.
**Agent artifacts:** this file and plugin steward.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
