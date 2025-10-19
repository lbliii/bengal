Title: Testing Strategy - Summary and Action Plan

Date: 2025-10-19

Status: Ready for Review

---

## TL;DR

**Your observation about the 95% long tail is spot-on.** Analysis reveals:

1. **`test_output_quality.py`** rebuilds a 292-page showcase site **11 times** (3-4 minutes)
2. **Stateful Hypothesis tests** generate 100+ build sequences (1-3 minutes)  
3. **Poor load balancing**: Fast tests finish quickly, workers idle while waiting for slow tests

**Quick wins (30 minutes of work)** can reduce the long tail from 3-5 minutes to <1 minute.

**Full RFC implementation** will systematically eliminate test duplication and improve ergonomics.

---

## Documents Created

### 1. `testing-strategy-enhancements-v2.md` - The RFC
**Comprehensive plan** for maturing Bengal's test suite, incorporating:
- Lessons from Sphinx's mature test infrastructure
- Specific fixes for Bengal's pain points
- Conservative approach (no over-engineering)
- Phased implementation (quick wins → full infrastructure)

**Key additions in v2**:
- More conservative snapshot strategy (deferred to Phase 5+)
- Specific cache cleanup targets identified from Bengal codebase
- Selective migration strategy (30-40 tests, not all 2,297)
- CLI runner supports both subprocess (integration) and click.testing (unit)
- **Phase 0: Quick Wins** added to address your long-tail issue immediately

### 2. `test-performance-analysis.md` - Root Cause Analysis
**Detailed investigation** of the 95% long-tail problem:
- Identified exact culprits with code examples
- Load balancing visualization
- Prioritized solutions with time estimates
- Validation commands to measure improvements

**Primary culprit**: `test_output_quality.py` uses function-scoped fixture for read-only tests on 292-page showcase site.

---

## Immediate Action Items (Phase 0: 30 minutes)

These address your long-tail frustration **right now**:

### 1. Fix `test_output_quality.py` Fixture Scope (5 minutes)

**File**: `tests/integration/test_output_quality.py`

**Change**:
```python
# Line 17: Change from function-scoped to class-scoped
@pytest.fixture(scope="class")  # ← Add scope="class"
def built_site(tmp_path_factory):  # ← Change tmp_path to tmp_path_factory
    """Build showcase site ONCE for all tests in TestOutputQuality class."""
    tmp_path = tmp_path_factory.mktemp("showcase_site")  # ← Add this line

    # ... rest stays the same ...
```

**Why it's safe**: All 11 tests are read-only assertions (no mutations).

**Impact**: 11 builds → 1 build = **saves 1.5-4 minutes**

### 2. Add Slow Marker (2 minutes)

**File**: `tests/integration/test_output_quality.py`

**Change**:
```python
import pytest  # ← Ensure imported

@pytest.mark.slow  # ← Add this decorator
class TestOutputQuality:
    """Test that built pages have expected quality and content."""
    ...
```

**Impact**: Devs can skip with `pytest -m "not slow"` for **~20s feedback loop**

### 3. Tune Hypothesis for Dev vs CI (5 minutes)

**File**: `tests/integration/stateful/test_build_workflows.py`

**Add at top** (after imports):
```python
import os
from hypothesis import settings

# Register profiles
settings.register_profile("ci", max_examples=100)   # Thorough for CI
settings.register_profile("dev", max_examples=20)   # Fast feedback for dev

# Load appropriate profile
settings.load_profile("dev" if os.getenv("CI") != "true" else "ci")
```

**Impact**: 100 examples → 20 in dev = **saves 30-90 seconds**

### 4. Validate Improvements (5 minutes)

```bash
# Measure before (if curious)
time pytest tests/integration/test_output_quality.py -v

# Apply changes above

# Measure after
time pytest tests/integration/test_output_quality.py -v
# Expected: Much faster (1 build instead of 11)

# Test dev workflow
time pytest -m "not slow" -n auto
# Expected: ~20 seconds

# Test full suite
time pytest -n auto
# Expected: ~1 minute (vs current 5-6 minutes)
```

### 5. Update Documentation (10 minutes)

**File**: `tests/README.md`

Add to the "Quick Runs" section:
```markdown
## Fast Development Workflow

For rapid feedback during development, skip slow integration tests:

```bash
# Fast feedback loop (~20s)
pytest -m "not slow" -n auto

# Before committing (full suite, ~1 min)
pytest -n auto
```

**What's marked slow**:
- Full showcase site builds (292 pages)
- Stateful Hypothesis tests (100+ sequences)
- Kitchen-sink integration tests

These still run in CI to ensure comprehensive coverage.
```

---

## Expected Results (Phase 0)

### Before
```
Test suite timeline:
0-95% complete:   ~20 seconds  (fast tests across workers)
95-100% complete: ~3-5 minutes (long tail: showcase + stateful tests)
Total:            ~5-6 minutes ← FRUSTRATING WAIT
```

### After Phase 0
```
Developer mode (pytest -m "not slow" -n auto):
Total: ~20 seconds ← FAST FEEDBACK

Full suite (pytest -n auto):
Total: ~1 minute ← Much better
```

### After Full RFC (Phases 1-3)
```
Developer mode: ~15 seconds (test roots faster than ad-hoc setup)
Full suite:     ~40-50 seconds (fixture reuse, minimal roots)
```

---

## Longer-Term Plan (RFC Implementation)

### What the RFC Adds

**1. Test Roots** (`tests/roots/test-<scenario>/`)
- Minimal, reusable site structures
- Eliminates 50-100 lines of setup per test
- Example: `test-basic` (1 page), `test-baseurl` (2 pages), `test-taxonomy` (3 pages)

**2. Pytest Marker** (`@pytest.mark.bengal`)
```python
@pytest.mark.bengal(testroot="test-basic")
def test_feature(site, build_site):
    build_site()
    assert site.pages[0].url == "/"
```

**3. CLI Runner Wrapper**
```python
from tests._testing.cli import run_cli

result = run_cli(["site", "build"], cwd=site_dir)
result.assert_ok()
assert "Build complete" in result.stdout
```

**4. Output Normalization**
- Strip timestamps, hashes, absolute paths
- Deterministic assertions
- Conservative snapshot strategy (narrow scope)

**5. HTTP Server Fixtures**
- Ephemeral servers for link/asset tests
- Wait-until-listen guards
- Clean teardown

**6. Cache Cleanup**
- Comprehensive state reset between tests
- No cross-test contamination

### Why It's Worth It

**Current test style** (readable but verbose):
```python
def test_build_with_path_baseurl(tmp_path: Path):
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    cfg = site_dir / "bengal.toml"
    cfg.write_text("""[site]\ntitle = "Test"\nbaseurl = "/bengal"\n...""")
    (site_dir / "content" / "index.md").write_text("""---\ntitle: Home\n---\n...""")

    site = Site.from_config(site_dir)
    orchestrator = BuildOrchestrator(site)
    orchestrator.build()

    html = (site_dir / "public" / "index.html").read_text()
    assert 'href="/bengal/assets/css/style' in html
```
**30 lines**, lots of duplication.

**After RFC** (ergonomic and clear):
```python
@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_build_with_path_baseurl(site, build_site):
    build_site()
    html = (site.output_dir / "index.html").read_text()
    assert 'href="/bengal/assets/css/style' in html
```
**8 lines**, clear intent, reusable fixture.

### Conservative Approach

**Not migrating everything**:
- Target 30-40 high-duplication tests (1.5% of suite)
- Leave unit tests alone (they're fast and clean)
- Keep simple integration tests as-is
- Migration is **opt-in**, not forced

**Snapshots deferred**:
- Initially use explicit assertions (clearer)
- Prove snapshot value incrementally (Phase 5+)
- Only snapshot stable structures (meta tags, nav hierarchy)
- Never snapshot full HTML (too brittle)

---

## Decision Points

### Now (After Phase 0)
✅ **Execute Phase 0 quick wins** (30 minutes)  
✅ **Measure impact** (should see 70-80% long-tail reduction)  
✅ If dramatic improvement → validates fixture scoping strategy

### After Review (Next Week)
✅ **Review RFC v2** with team  
✅ **Decide**: Proceed to Phase 1 infrastructure? Adjust approach?

### After Phase 1-2 (2 weeks)
✅ **Prototype validation**: Does `@pytest.mark.bengal` feel ergonomic?  
✅ **Performance validation**: Are test roots faster than ad-hoc setup?  
✅ **Decide**: Continue to Phase 3 (broader migration) or stop at infrastructure?

---

## Questions for Discussion

1. **Phase 0**: Should we apply the quick wins immediately? (High confidence, low risk)

2. **RFC Strategy**: Does the phased, selective approach feel right? Any concerns?

3. **Snapshot Scope**: Agree with deferring snapshots until we prove value?

4. **Migration Target**: 30-40 tests (1.5% of suite) sufficient, or aim higher?

5. **CI Impact**: Current CI runs full suite; should we have separate "fast" and "full" jobs?

---

## Resources

- **RFC**: `testing-strategy-enhancements-v2.md` (comprehensive plan)
- **Analysis**: `test-performance-analysis.md` (root cause details)
- **This Summary**: Quick reference and action items

**Next Step**: Review this summary, then either:
- Execute Phase 0 quick wins immediately, OR
- Schedule RFC review meeting to discuss approach
