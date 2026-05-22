<!-- markdownlint-disable MD013 -->

# Steward Questions

These are the targeted SME questions the bootstrap could not answer from source,
tests, docs, changelog, workflows, or grep-verifiable history. Do not invent
answers; update the relevant steward when an answer becomes policy.

## Root Constitution

- Which humans or teams should be encoded as CODEOWNERS for public API, release,
  docs, and security-sensitive changes?
- What ty diagnostic floor should replace the current approximate root guidance?
- Which public guarantees are strategic commitments versus current alpha behavior?

## Core

- Which `Site`, `Page`, and `Section` attributes are intentionally public for
  third-party code, not just template compatibility?
- What is the planned removal horizon for remaining Site lifecycle shims?
- Which core import-linter ignores are acceptable long term, if any?

## Core Page

- Which Page compatibility properties are guaranteed through 1.0?
- Which Page bundle behaviors are public API versus theme convenience?
- Should Page expose deprecation warnings for any remaining shim slated for removal?

## Core Section

- Which Section navigation attributes are public to templates versus internal?
- Are versioned-section URL guarantees different from unversioned section URLs?
- Should `section.subsections` ordering be treated as an API contract?

## Core Site

- Which composed services on Site are public entrypoints?
- What lifecycle methods should remain on Site after compatibility shims expire?
- Should Site initialization validate more eagerly, or remain mostly passive?

## Rendering

- Which template context keys are stable public contracts for custom themes?
- What is the expected compatibility policy for Kida upgrades?
- Which rendering helpers should be documented as supported extension points?

## Rendering Pipeline

- Are `ParsedPage` and `RenderedPage` intended to become public importable API?
- Which dependency kinds must always be recorded for selective rebuilds?
- Should missing output collector propagation be a hard error or diagnostic only?

## Template Functions

- Which helpers are stable public API and which are internal theme helpers?
- Should generated reference docs include all registered helpers by default?
- What deprecation process should helper renames follow?

## Orchestration

- Which build lifecycle diagnostics are part of the CLI contract?
- Should plugin phase hook order be documented as stable?
- What is the acceptable fallback policy when selective rebuild evidence is incomplete?

## Build Phases

- Which existing hardcoded phases are considered extension points?
- Should phase timings and output collector records have a machine-readable schema?
- Are build phase names public enough to require migration notes?

## Incremental Orchestration

- What artifacts define full/warm parity for release readiness?
- What cache/provenance divergence policy should be canonical?
- Which missed invalidation classes should force full rebuild immediately?

## Build Contracts

- Which dependency key formats are externally visible?
- Should detector result types be versioned or migration-aware?
- Which old build contract aliases can be removed before 1.0?

## Cache

- What cache schema versioning policy should Bengal follow?
- When corruption is detected, should Bengal clear one cache, all caches, or fail?
- Which cache files are safe for users/CI to persist across Bengal versions?

## Snapshots

- Which mutable render-time reads still need snapshot migration?
- Should snapshot construction precompute navigation trees by default?
- Which snapshot fields are public debug output versus internal implementation?

## CLI

- Which aliases are guaranteed to remain (`b`, `s`, `v`, `c`)?
- What is the compatibility policy for changing command output templates?
- Should CLI JSON output schemas be versioned?

## Config

- Which config keys are stable through 1.0?
- What is the formal precedence order across files, profiles, environments, env vars, and CLI flags?
- Should unknown config keys be warnings or hard errors by default?

## Protocols

- Which protocols are intended for third-party implementers?
- What is the deprecation window for protocol attribute or method changes?
- Should protocol docs mark implementation-only protocols separately?

## Plugins

- Which of the nine plugin extension points are production-ready?
- Should plugin capability metadata have a formal schema?
- What compatibility promise should Bengal make for `bengal.plugins` discovery?

## Errors

- Which error codes are stable public identifiers?
- Should every `BengalError` require `debug_payload`, or only user-boundary errors?
- What JSON error format compatibility policy should releases follow?

## Content

- Which content source APIs are public versus experimental?
- What remote-source failure modes should degrade gracefully versus fail the build?
- How should versioned shared content resolve conflicts across versions?

## Content Types

- Is `ContentTypeStrategy` a public extension API for 1.0?
- Which generated strategy TODOs should become stronger scaffold guidance?
- Should strategy matching order be documented as stable?

## Parsing

- Which directive syntaxes are committed public contracts?
- What CommonMark compatibility level is Bengal targeting?
- Should parser failures prefer diagnostics with partial output or hard errors?

## Autodoc

- Which Python members are documented by default when `__all__` is absent?
- What source-link behavior is expected for non-GitHub repositories?
- Which generated autodoc layouts are considered stable for custom themes?

## Scaffolds

- Which scaffold templates are supported long term?
- Should scaffold outputs include comments explaining Bengal conventions?
- What generated-site smoke test is required before adding a new scaffold?

## Assets

- Which asset manifest fields are public?
- Should missing tracked assets fail strict builds by default?
- What browser asset compatibility targets matter for default generated sites?

## Default Theme

- Which CSS variables and template blocks are public customization API?
- What accessibility baseline should the default theme enforce?
- Which swizzled template moves require migration notes?

## Server

- What latency/reload target should local preview defend?
- Should watcher fallbacks fail closed or keep serving stale output with warnings?
- Which Pounce behaviors are Bengal-owned contracts versus delegated dependency behavior?

## Health

- Which validators are release gates versus advisory checks?
- What report fields are stable for external automation?
- Should `bengal fix` require confirmation for any remediation class?

## Postprocess

- Which generated artifact file names are stable public output contracts?
- Should output format schemas be versioned?
- What minimum artifact set defines a valid docs build?

## Audit

- Which audit findings should block release?
- Should audit output be optimized for humans, machines, or both?
- What verification receipts should audit reports preserve by default?

## Utilities

- Which utility modules are public import paths?
- What concurrency primitives are preferred for new shared state?
- Should path/link helpers document platform-specific behavior?

## Site Documentation

- Which product claims are strategic but not yet fully proven?
- Who owns final accuracy for generated reference docs?
- What docs build/linkcheck gates should be required before release?

## Planning

- Which plan statuses are canonical (`drafted`, `complete`, `superseded`, `stale`)?
- When should a plan be archived after implementation?
- Should accepted architecture decisions be copied from `plan/` into public docs?

## Tests

- What coverage target is current and enforced?
- Which test markers are CI contracts versus local convenience?
- When is a snapshot acceptable instead of focused assertions?

## Unit Tests

- Which public mocks are guaranteed to track real contracts?
- Should unit tests forbid importing generated site fixtures?
- What is the expected maximum runtime for unit-only feedback?

## Integration Tests

- Which workflows are release blockers?
- How often should `.test_durations` be regenerated?
- What fixture complexity is acceptable before a test should become an e2e case?

## Performance Tests

- Which performance budgets are release blockers?
- What hardware/runtime metadata must accompany benchmark results?
- Which benchmarks should run under Python 3.14t specifically?

## Benchmarks

- Which benchmark scenarios map to public performance claims?
- How should baseline files be reviewed and updated?
- What cleanup policy should generated benchmark scenarios follow?

## Syntax Highlighter Package

- Is the VS Code grammar maintained and released independently from Bengal?
- Which Kida/Bengal syntax features should editor support prioritize?
- Should this package stay in the repo or move to a separate release project?
