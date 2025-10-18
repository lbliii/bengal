Title: Consolidate BuildContext and finalize incremental bridge

Context
- Two BuildContext definitions existed: `bengal/core/build_context.py` and `bengal/utils/build_context.py`.
- Tests and new orchestration use DI via BuildContext, and incremental bridge stubs existed.

Edits
- `bengal/core/build_context.py`: convert to compatibility shim re-exporting `bengal.utils.build_context.BuildContext`.
- `bengal/orchestration/incremental.py`:
  - Import BuildContext from utils.
  - Implement `process(change_type, changed_paths)` using tracker.invalidator and write outputs.
  - Fix `_write_output` to derive pretty URL paths from content dir, writing placeholder HTML.
- `bengal/orchestration/full_to_incremental.py`:
  - Replace stub with `run_incremental_bridge(site, change_type, changed_paths)` helper that initializes cache then calls `process`.

Rationale
- Single canonical BuildContext reduces drift and import ambiguity.
- Bridge enables tests and future dev server flows to simulate incremental without full orchestrator.
- Output writer mirrors pretty URL behavior for correctness in tests.

Follow-ups
- Thread BuildContext deeper into rendering/postprocess consumers incrementally.
- Expand bridge to map templates to affected pages via cache (already supported).
