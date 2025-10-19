# CI Workflow Improvements for Phase 0 Test Changes

## Current Issue

Your CI workflow needs a small update to work optimally with the Phase 0 test improvements:

**Problem**: Hypothesis profile selection
- Our tests now use different Hypothesis profiles: dev (20 examples) vs CI (100 examples)
- Selection is based on `os.getenv("CI")`
- **GitHub Actions does NOT set CI=true by default**
- Result: CI is using the dev profile (20 examples) instead of CI profile (100 examples)

## Minimal Fix (APPLIED)

Added `CI: true` environment variable to test steps in `.github/workflows/tests.yml`:

```yaml
- name: Run targeted baseurl portability tests
  env:
    BENGAL_BASEURL: ${{ matrix.baseurl }}
    CI: true  # ← Added: Tells Hypothesis to use CI profile (100 examples)
  run: |
    pytest ...

- name: Run full test suite (single env only)
  env:
    CI: true  # ← Added: Tells Hypothesis to use CI profile (100 examples)
  run: |
    pytest ...
```

**Impact**:
- CI now runs 100 Hypothesis examples (thorough)
- Dev still runs 20 examples (fast feedback)
- No other changes to current workflow

## Optional Enhancement (see tests-improved.yml.suggestion)

For even better CI performance, consider a two-stage approach:

### Stage 1: Fast Check (~20s)
```yaml
fast-check:
  runs-on: ubuntu-latest
  steps:
    - run: pytest -m "not slow" -n auto
```
- Runs in ~20 seconds
- Gives quick feedback on PRs
- Skips showcase build and stateful tests

### Stage 2: Full Suite (~1-2 min)
```yaml
full-suite:
  needs: fast-check  # Only runs if fast-check passes
  steps:
    - run: pytest -v --cov=bengal  # All tests including slow
```
- Only runs if fast-check passes
- Includes all tests (slow markers + coverage)
- Matrix tests still run

**Benefits**:
- Fail fast on common issues (20s vs 2min)
- Save CI minutes (don't run slow tests if fast ones fail)
- Better developer experience (quicker feedback)

**Trade-off**:
- Slightly more complex workflow
- Two jobs instead of one
- May take longer if fast-check passes (sequential)

## Recommendation

**For now**: Use the minimal fix (CI: true) ✅ DONE

**Later**: Consider fast-check if you want to optimize CI experience further

## Testing

To verify CI will work correctly:

```bash
# Simulate CI environment locally
CI=true pytest tests/integration/stateful/ -v --hypothesis-show-statistics

# Should show: max_examples=100 (not 20)
```

## Summary

✅ **Minimal fix applied**: Added `CI: true` to workflow
✅ **CI will now use 100 Hypothesis examples** (thorough testing)
✅ **No breaking changes to existing workflow**
⚠️ **Optional enhancement available** if you want faster PR feedback
