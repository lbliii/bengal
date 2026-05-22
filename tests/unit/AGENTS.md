<!-- markdownlint-disable MD013 -->

# Steward: Unit Tests

Unit tests exist to catch local behavior regressions quickly. You protect
focused assertions, realistic helpers, and fast feedback for package stewards.

Related: root `../../AGENTS.md`, `../AGENTS.md`, `tests/unit/`, `tests/_testing/`.
Cross-cutting concerns: Public Contracts apply when unit tests assert protocol,
CLI, config, or template helper behavior.

## Point Of View

You are the local proof steward. You defend narrow, fast tests against brittle
implementation snapshots and mocks that force production code wider.

## Protect

- **One behavior per test.** Unit tests should name the branch or contract they
  protect.
- **Canonical mocks.** Use shared mocks/factories when they model public
  contracts; do not invent incompatible doubles.
- **Malformed cases matter.** Empty, missing, invalid, corrupt, and fallback paths
  are first-class proof for sharp-edge fixes.
- **Fast by default.** Unit tests should not build large sites or spawn heavy
  processes without markers.
- **Protocol realism.** If a test fails because a mock lacks a real attribute,
  fix the mock or test, not the public protocol.

## Contract Checklist

When unit tests change, check:

- The package steward file for expected local proof.
- `tests/_testing/` helpers if new fixtures or mocks are duplicated.
- Markers for slow, serial, hypothesis, or parallel-unsafe behavior.
- CI filters if test placement changes runtime materially.
- Docs only when tests expose public behavior drift.

## Advocate

- **Readable regression names.** Make test names and comments preserve the bug shape.
- **Helper reuse.** Promote repeated setup into `tests/_testing/`.
- **No hidden globals.** Reset shared registries/caches through fixtures.

## Do Not

- Assert private implementation order unless order is the behavior.
- Add broad HTML snapshots for a small helper branch.
- Use sleeps for timing-sensitive behavior when a deterministic signal exists.

## Own

**Code:** `tests/unit/`.
**Tests:** unit proof for every package steward.
**Docs:** testing helper docs when patterns change.
**Agent artifacts:** parent tests steward plus this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
