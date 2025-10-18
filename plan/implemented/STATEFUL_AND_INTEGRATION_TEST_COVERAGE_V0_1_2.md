# 0.1.2 Test Coverage Plan – Stateful + Integration Stability

**Owner**: Core
**Status**: Draft
**Release Target**: 0.1.2 (patch)

---

## Objectives
- Ensure deleted/renamed content and assets never leave stale output in `public/`.
- Guarantee incremental builds produce the same output set/content as full builds.
- Improve confidence via property/stateful tests across critical lifecycles.
- Reduce test flakiness and align invariants with build lifecycle.

## Exit Criteria (0.1.2)
- All new stateful/integration tests pass locally and in CI.
- “Incremental equals full” property validated for content, templates, and taxonomy.
- Baseline explicit integration test for deleted page cleanup passes.
- No regressions in runtime (±10%) for test suite compared to 0.1.1.

## Scope
1) Page lifecycle
- create → build → modify → build → delete → build
- re-create same name after delete
- rename/move across sections

2) Assets lifecycle
- add → build → delete → build
- fingerprint changes propagate to references (if applicable)

3) Template/partial changes
- modify theme template/partial → affected pages rebuild
- no orphan outputs due to template-only changes

4) Taxonomy-generated pages
- add/remove tags in page frontmatter
- tag pages and tag index reflect current tags; orphan tag pages removed

5) Config changes
- `bengal.toml` modifications force full rebuild when appropriate
- cache remains consistent; no stale outputs post-change

6) Postprocess outputs
- `sitemap.xml`, `rss.xml`, and output formats stay in sync with current pages
- no orphans after deletions

7) Directory hygiene
- empty parent directories under `public/` pruned after deletions (best-effort)

8) Idempotence & crash-safety
- two identical builds produce identical output set and hashes
- simulate interrupted build (skip final cache save) and verify next full build returns to correctness

## Test Additions

### A. Extend PageLifecycleWorkflow
- Add rules:
  - rename_page(old -> new)
  - move_page(section change)
  - add_tag/remove_tag on a random page
  - modify_template_or_partial
  - modify_config
- Invariants (run only post-build):
  - active pages have output; deleted/renamed old URLs do not
  - tag pages reflect current tags; no orphan tag pages
  - “incremental equals full” after sequences including template/taxonomy changes

### B. AssetLifecycleWorkflow (new)
- Rules: add asset, delete asset, modify asset
- Invariants (post-build):
  - deleted assets’ outputs removed
  - if fingerprinting present, references update (hash changes cause new file name)

### C. Postprocess validation (integration)
- After build, assert `sitemap.xml` and `rss.xml` include/omit pages according to current state.
- Deleting pages removes them from postprocess outputs.

### D. Baseline explicit tests
- `test_deleted_page_cleanup()` – simple non-stateful test to guard the core behavior.
- Idempotence test – two consecutive identical builds produce identical hashes.

### E. Unit tests for cleanup plumbing
- `BuildCache.track_output()` basic mapping coverage
- `IncrementalOrchestrator._cleanup_deleted_files()` with temp dirs

## Implementation Notes
- Invariants must only evaluate immediately after build rules. We set a `last_action_was_build` flag and early-return otherwise.
- The parsed-content cache access bug was fixed by using `dependency_tracker.cache` (not `_cache`), improving incremental behavior and reducing test timing flakiness.
- Keep stateful tests fast: minimize large file generation; reuse small site fixtures.

## Acceptance Metrics
- New tests added:
  - 1 new workflow file for assets
  - 4–6 new rules in page lifecycle workflow
  - 2 baseline explicit tests
  - 2 small unit tests
- Hypothesis runs complete within CI time budget (tune max examples if needed).

## Risks & Mitigations
- Flaky timing in filesystem ops → prefer deterministic file writes and immediate fs checks post-build.
- Over-broad invariants → keep gating strictly to post-build states.
- CI timeouts → cap Hypothesis examples in CI via env/config; allow extended runs locally.

## Timeline (short)
- Day 1: Land invariant gating (done) and pipeline cache fix (done). Draft plan.
- Day 2: Implement baseline tests + taxonomy/template rules.
- Day 3: Implement assets workflow + postprocess assertions.
- Day 4: Add rename/move rules + unit tests; tune Hypothesis settings for CI.
- Day 5: Stabilize, document, and finalize for 0.1.2.

## Deliverables
- `tests/integration/stateful/test_build_workflows.py` (extended)
- `tests/integration/stateful/test_asset_workflows.py` (new)
- `tests/integration/test_deleted_page_cleanup.py` (new)
- `tests/unit/cache/test_build_cache_mapping.py` (new)
- `tests/unit/orchestration/test_cleanup_deleted_files.py` (new)
- CHANGELOG 0.1.2 entries for stability improvements

---

## Follow-up (Post-0.1.2 – Design)
- Manifest-based cleanup for comprehensive orphan detection across all outputs.
- Add `--no-cleanup` and config toggle for debugging edge cases.
