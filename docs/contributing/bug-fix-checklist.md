# Bug Fix Checklist

When fixing a bug, follow this checklist to prevent regressions and document the fix.

## 1. Add a Regression Test

**Rule**: Every bug fix should include a test that would have caught the bug.

- [ ] Identify the **conditions** that triggered the bug:
  - Parallel vs sequential rendering?
  - Page count (e.g. 5+ pages enables parallel)?
  - Environment (production vs local)?
  - Specific template or layout?
- [ ] Add a test that exercises those conditions
- [ ] Assert the build completes without errors
- [ ] (Optional) Temporarily revert the fix and verify the test fails

**Example**: K-RUN-007 (newsletter_cta Undefined) only occurred on full rebuild with parallel rendering. The regression test uses `test-blog-paginated` (28 pages) and `build_site(parallel=True)` — see `tests/integration/test_parallel_rendering.py`.

## 2. Document in Research (If Complex)

For bugs that required investigation:

- [ ] Create or update a research doc in `docs/research/`
- [ ] Include: reproduction steps, root cause hypothesis, fix, and regression test reference

## 3. Update Changelog

- [ ] Add an entry to `changelog.md` under the appropriate scope
- [ ] Use past tense, be specific about the fix
