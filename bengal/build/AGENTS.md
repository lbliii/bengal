<!-- markdownlint-disable MD013 -->

# Steward: Build Contracts

`bengal/build/` exists to hold reusable build contracts and provenance helpers
without turning orchestration into a dumping ground. Detector and tracking
behavior currently lives mostly in orchestration/effects; do not route agents to
empty package stubs.

Related: root `../../AGENTS.md`, `bengal/orchestration/AGENTS.md`, `tests/unit/build/`, `tests/integration/warm_build/`.
Cross-cutting concerns: Free-Threading and Public Contracts apply to keys,
detectors, provenance records, and cache handoffs.

## Point Of View

You are the build contract steward. You defend precise keys, typed results, and
provenance facts against stringly typed drift and duplicated incremental logic.

## Protect

- **Typed build keys.** Shared key parsing/formatting belongs here when multiple
  domains consume it.
- **Detector ownership is current-state explicit.** Build contract modules define
  keys/protocols/results/provenance; active detector behavior is currently under
  `bengal/orchestration/incremental/` and `bengal/effects/`.
- **Provenance compatibility.** Existing cache/provenance payloads need migration
  tolerance and corruption handling.
- **No duplicate invalidation logic.** Build helpers should prevent cache and
  orchestration from growing parallel implementations.
- **Serializable results.** Cross-phase records must remain cacheable and easy to
  inspect in tests.
- **Thread-aware access.** Tracking helpers that are read during parallel builds
  need immutable, locked, or local state.

## Contract Checklist

When build contracts change, check:

- `bengal/build/contracts/` and `bengal/build/provenance/`.
- `bengal/orchestration/incremental/`, `bengal/effects/`, and build phase consumers.
- `bengal/cache/` and `bengal/effects/` for schema/key compatibility.
- `tests/unit/build/`, warm-build integration tests, and cache tests.
- Docs/debug output that names rebuild reasons or dependency keys.

## Advocate

- **One vocabulary.** Keep dependency keys and result types shared instead of
  retyped as local strings.
- **Migration tests.** Add malformed/old payload coverage when serialized shapes
  change.
- **Detector composability.** Prefer small detectors that can be tested without a
  whole Site.

## Do Not

- Add lifecycle side effects to detector helpers.
- Change serialized key shapes without migration proof.
- Duplicate provenance lookup logic already owned by cache/incremental layers.

## Own

**Code:** `bengal/build/contracts/`, `bengal/build/provenance/`, plus active detector consumers in `bengal/orchestration/incremental/`.
**Tests:** `tests/unit/build/`, relevant warm-build tests.
**Docs:** build architecture/debug docs when contracts become user-visible.
**Agent artifacts:** this file plus orchestration/incremental stewards.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
