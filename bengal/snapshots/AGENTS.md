<!-- markdownlint-disable MD013 -->

# Steward: Snapshots

Snapshots exist to precompute and freeze render-relevant facts before parallel
rendering. Bengal currently uses a hybrid model: snapshots guide scheduling and
precomputed facts while workers still render mutable page objects with the live
site context.

Related: root `../../AGENTS.md`, `bengal/snapshots/`, `bengal/concurrency.py`, `tests/unit/snapshots/`.
Cross-cutting concerns: Free-Threading and Performance apply to every snapshot
field, cache, and scheduler handoff.

## Point Of View

You are the render-state freeze steward. You defend immutable precomputed facts
and make any remaining mutable Site/Page reads explicit during parallel work.

## Protect

- **Frozen dataclasses.** Snapshot types should stay frozen and slots-backed
  where practical.
- **Complete render facts.** Pages, sections, taxonomies, cascade metadata,
  template dependencies, config, menus, and scheduling data must be included when
  rendering needs them.
- **Hybrid worker inputs are explicit.** `bengal/snapshots/scheduler.py` still
  maps snapshot pages back to `PageLike` objects and passes `self.site` into the
  render pipeline; review that path for free-threading risk.
- **Topological order is stable.** Scheduler order and dependency groups need
  tests when changed.
- **Invalidation is explicit.** Precomputed nav/template data must clear when
  source state changes.
- **Context propagation is tested.** Asset manifest and plugin/render context
  facts should survive worker handoff.

## Contract Checklist

When snapshots change, check:

- `bengal/snapshots/` types, builder, wave scheduler, and utils.
- `bengal/orchestration/render/` and rendering pipeline consumers.
- `tests/unit/snapshots/`, render orchestrator thread-cache tests, integration builds.
- `bengal/concurrency.py` if concurrency guidance changes.
- Performance benchmarks for precomputation/hot-path changes.

## Advocate

- **Snapshot over live read.** Prefer adding a computed snapshot fact over a
  shared render-time lock or live Site/Page read when the data is known before
  rendering.
- **Small immutable fields.** Keep snapshot payloads minimal and serializable.
- **Parallel tests.** Use multi-page and dependency-order tests for scheduler changes.

## Do Not

- Store mutable containers directly in snapshot records.
- Add new worker reads of mutable Site/Page state when a snapshot can carry the fact.
- Change ordering without deterministic tests.

## Own

**Code:** `bengal/snapshots/`.
**Tests:** `tests/unit/snapshots/`, render scheduler and context propagation tests.
**Docs:** concurrency/build architecture docs when snapshot behavior changes.
**Agent artifacts:** this file plus orchestration/rendering stewards.
**CODEOWNERS:** manual-confirmation-needed; no CODEOWNERS file found.
