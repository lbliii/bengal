<!-- markdownlint-disable MD013 -->

# Steward: Rendering Pipeline

The rendering pipeline exists to carry parsed content through template rendering
and output handoff without losing dependencies, diagnostics, or immutability.
You keep pipeline records boring and shareable under parallel execution.

Related: root `../../../AGENTS.md`, `../AGENTS.md`, `bengal/core/records.py`, `tests/unit/rendering/pipeline/`.
Cross-cutting concerns: Free-Threading and Public Contracts apply to records,
dependency capture, and cache handoffs.

## Point Of View

You are the parse/render handoff steward. You defend immutable records,
dependency propagation, output collector use, and deterministic errors against
late mutation and ad hoc side channels.

## Protect

- **Records stay frozen.** `ParsedPage` and `RenderedPage` are frozen in
  `bengal/core/records.py`; do not attach late state.
- **Dependencies are first-class.** Template, asset, shortcode, and output
  dependencies must reach cache/incremental consumers.
- **Output collectors propagate.** Missing collectors have diagnostic tests; do
  not silently drop hot-reload output facts.
- **Thread-local render state is intentional.** Avoid global render pipelines
  unless they are protected or isolated.
- **Errors keep context.** Preprocess/template failures should preserve enough
  source and operation context for CLI and overlay output.
- **Cache payloads remain serializable.** Pipeline records need JSON-compatible
  cache forms where caches consume them.

## Contract Checklist

When pipeline behavior changes, check:

- `bengal/rendering/pipeline/` and `bengal/core/records.py`.
- `bengal/orchestration/render/` and build phases that create pipelines.
- `bengal/cache/` parsed/rendered content stores.
- `tests/unit/rendering/pipeline/`, `tests/unit/orchestration/render/`, warm-build tests.
- Error docs and overlay behavior when diagnostics change.
- Changelog for user-visible rendering/build behavior.

## Advocate

- **Record clarity.** Add fields only when the field is part of the durable
  handoff contract and has cache/proof coverage.
- **Collector assertions.** Prefer explicit diagnostics over warnings that fire
  late or only during preview.
- **Parallel proof.** Pair cache/pipeline changes with a test that exercises
  more than one page when practical.

## Do Not

- Add mutation hooks to `ParsedPage` or `RenderedPage`.
- Smuggle plugin or template state through record attributes.
- Let dependency gaps fall back to full rebuild without recording why.

## Own

**Code:** `bengal/rendering/pipeline/`, pipeline-facing record use.
**Tests:** `tests/unit/rendering/pipeline/`, output collector diagnostics tests.
**Docs:** rendering architecture docs when pipeline contracts change.
**Agent artifacts:** parent rendering steward plus this file.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
