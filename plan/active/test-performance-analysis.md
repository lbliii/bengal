Title: Test Suite Performance Analysis - The Long Tail Problem

Status: Analysis / Action Items

Date: 2025-10-19

---

## Problem Statement

Test suite runs fast until ~95% completion, then hangs for minutes on the last 5-10 tests. This creates a frustrating developer experience where you're stuck waiting despite most tests finishing quickly.

## Root Cause Analysis

### Issue 1: Function-Scoped Showcase Site Builds (PRIMARY CULPRIT)

**File**: `tests/integration/test_output_quality.py`

**Problem**:
```python
@pytest.fixture
def built_site(tmp_path):
    """Build a complete site and return the output directory."""
    # Copy showcase example to tmp
    showcase = Path("examples/showcase")
    site_dir = tmp_path / "site"

    shutil.copytree(showcase / "content", site_dir / "content")  # 292 files!
    shutil.copy(showcase / "bengal.toml", site_dir / "bengal.toml")

    site = Site.from_config(site_dir)
    site.config["strict_mode"] = True
    site.build()  # Full build of 292 pages

    return site.output_dir
```

**Impact**:
- Fixture is **function-scoped** (rebuilds for every test)
- Used by **11 tests** in `TestOutputQuality` class
- Showcase has **292 content files**
- **11 full builds × 292 pages = 3,202 page renders**
- Estimated time: **2-5 minutes** depending on hardware

**Why it's in the long tail**:
- With `pytest -n auto`, fast unit tests complete quickly across workers
- Workers become idle while waiting for the 11 slow showcase builds to finish
- Load balancing issue: one worker gets stuck building showcase repeatedly

**Tests affected**:
```
test_pages_include_theme_assets
test_pages_have_proper_html_structure
test_pages_have_reasonable_size
test_pages_contain_actual_content
test_no_unrendered_jinja2_in_output
test_theme_assets_copied
test_pages_have_proper_meta_tags
test_rss_feed_generated
test_sitemap_generated
test_404_page_generated
test_search_index_generated
```

**All of these tests are READ-ONLY** - they don't modify the built site!

### Issue 2: Hypothesis Stateful Tests (SECONDARY CULPRIT)

**File**: `tests/integration/stateful/test_build_workflows.py`

**Problem**:
```python
class PageLifecycleWorkflow(RuleBasedStateMachine):
    """Simulates realistic page management workflows."""
    # Generates hundreds of sequences of operations
    # Each sequence does multiple builds

TestPageLifecycleWorkflow = PageLifecycleWorkflow.TestCase
TestIncrementalConsistencyWorkflow = IncrementalConsistencyWorkflow.TestCase
```

**Impact**:
- 2 stateful test classes
- Each generates **100+ operation sequences** (Hypothesis default)
- Each sequence does **multiple site builds** (create → build → modify → build → etc.)
- These cannot run in parallel (stateful nature)
- Estimated time: **1-3 minutes total**

**Why it's in the long tail**:
- Stateful tests are inherently sequential
- Long-running individual test cases
- Block a worker while generating/executing sequences

### Issue 3: Load Balancing with `pytest-xdist`

**Problem**: pytest-xdist (`-n auto`) distributes tests to workers, but:
- Fast tests (unit) finish in milliseconds
- Slow tests (integration) take seconds to minutes
- Workers sit idle after finishing their fast tests
- A few workers get "unlucky" with slow tests

**Visual representation**:
```
Time →
Worker 1: [fast][fast][fast][fast][fast] ................. IDLE
Worker 2: [fast][fast][fast][fast] ................. IDLE
Worker 3: [fast][fast][SHOWCASE BUILD 1].......[SHOWCASE BUILD 2]......
Worker 4: [fast][fast][fast][STATEFUL TEST]........................
          ↑                                              ↑
      95% complete                                  Last 5%
      (1 second)                                  (2-3 minutes)
```

## Measurement (Before Fix)

Let's measure the actual impact:

```bash
# Run just the problem tests
time pytest tests/integration/test_output_quality.py -v

# Run stateful tests
time pytest tests/integration/stateful/ -v --hypothesis-show-statistics

# Full suite with timing
pytest --durations=20 -v
```

Expected output:
```
SLOWEST 20 TEST DURATIONS:
150.00s - test_output_quality.py::TestOutputQuality (aggregate)
 45.00s - test_build_workflows.py::TestPageLifecycleWorkflow
 30.00s - test_build_workflows.py::TestIncrementalConsistencyWorkflow
  2.50s - test_full_to_incremental_sequence.py::test_...
  ...
```

## Solutions (Prioritized by Impact)

### Solution 1: Change `built_site` Fixture to Class Scope (HIGH IMPACT, 5 minutes work)

**Change**:
```python
# tests/integration/test_output_quality.py

# Before:
@pytest.fixture
def built_site(tmp_path):
    ...

# After:
@pytest.fixture(scope="class")
def built_site(tmp_path_factory):
    """Build showcase site ONCE for all tests in TestOutputQuality class."""
    tmp_path = tmp_path_factory.mktemp("showcase_site")
    showcase = Path("examples/showcase")
    site_dir = tmp_path / "site"

    shutil.copytree(showcase / "content", site_dir / "content")
    shutil.copy(showcase / "bengal.toml", site_dir / "bengal.toml")

    site = Site.from_config(site_dir)
    site.config["strict_mode"] = True
    site.build()

    return site.output_dir
```

**Impact**:
- **11 builds → 1 build**
- Estimated time saved: **1.5-4 minutes** (depending on hardware)
- Zero risk: tests are already read-only
- Works with existing code

**Validation**:
All tests in `TestOutputQuality` are assertions on built output:
- ✅ No mutations to files
- ✅ No state changes
- ✅ Pure read operations (BeautifulSoup parsing, file size checks, string assertions)

### Solution 2: Add `pytest.mark.slow` to Showcase Tests (MEDIUM IMPACT, 2 minutes work)

**Change**:
```python
@pytest.mark.slow
class TestOutputQuality:
    """Test that built pages have expected quality and content."""
    ...
```

**Impact**:
- Developers can skip with `pytest -m "not slow"` for fast feedback
- CI can run full suite
- Estimated time saved for devs: **1-4 minutes** (when skipping)

### Solution 3: Reduce Hypothesis Examples for Dev (MEDIUM IMPACT, 5 minutes work)

**Change**:
```python
# tests/integration/stateful/test_build_workflows.py

from hypothesis import settings

# Add at module level
settings.register_profile("ci", max_examples=100)  # Thorough
settings.register_profile("dev", max_examples=20)  # Fast feedback
settings.load_profile("dev" if os.getenv("CI") != "true" else "ci")

class PageLifecycleWorkflow(RuleBasedStateMachine):
    ...
```

Or in `pytest.ini`:
```ini
[pytest]
addopts = --hypothesis-profile=dev
```

**Impact**:
- **100 examples → 20 examples** in dev
- Estimated time saved: **30-90 seconds**
- Still thorough in CI

### Solution 4: Use `pytest-xdist` Load Balancing Mode (LOW IMPACT, 1 minute work)

**Change**:
```bash
# Instead of:
pytest -n auto

# Use:
pytest -n auto --dist loadscope  # or loadgroup
```

**Impact**:
- Better distribution of slow tests across workers
- Modest improvement (~10-20% on long tail)
- May not help much with very slow individual tests

### Solution 5: Split Showcase Tests by Speed (FUTURE, part of RFC)

Create two test classes:
```python
@pytest.fixture(scope="class")
def built_showcase_site(tmp_path_factory):
    """Build showcase once."""
    ...

class TestShowcaseStructure:
    """Fast structural tests."""
    def test_has_head(self, built_showcase_site): ...
    def test_has_nav(self, built_showcase_site): ...

@pytest.mark.slow
class TestShowcaseContent:
    """Slow content validation tests."""
    def test_no_unrendered_jinja2(self, built_showcase_site):
        # Iterates over ALL pages
        ...
```

## Implementation Plan

### Immediate (Today, 10 minutes)

1. ✅ Change `built_site` fixture to `scope="class"` in `test_output_quality.py`
2. ✅ Add `@pytest.mark.slow` to `TestOutputQuality` class
3. ✅ Run tests to validate: `pytest tests/integration/test_output_quality.py -v`
4. ✅ Measure improvement: `time pytest tests/ -m "not slow"`

### Short-term (This Week, 15 minutes)

5. ✅ Add Hypothesis profile configuration for dev vs CI
6. ✅ Document in `tests/README.md`:
   ```markdown
   ## Fast Development Workflow

   Skip slow integration tests for rapid feedback:
   ```bash
   pytest -m "not slow" -n auto  # ~20s instead of ~5min
   ```

   Full suite (run before committing):
   ```bash
   pytest -n auto  # ~5min
   ```
   ```

### Medium-term (Part of RFC Implementation)

7. ✅ Create minimal test roots to replace showcase in most tests
8. ✅ Reserve showcase tests for "kitchen sink" validation only
9. ✅ Introduce session-scoped pre-built site fixtures for common scenarios

## Expected Impact

### Before Fix
```
Fast tests (0-95%):     ~20 seconds  ████████████████████
Long tail (95-100%):   ~3-5 minutes  ████████████████████████████████████████████████████
Total:                  ~5-6 minutes
```

### After Solution 1 (Class-Scoped Fixture)
```
Fast tests (0-95%):     ~20 seconds  ████████████████████
Long tail (95-100%):    ~30-60 sec   ██████
Total:                   ~1 minute
```

### After Solutions 1+2+3 (+ Hypothesis Tuning)
```
Developer mode (-m "not slow"):  ~20 seconds  ████
CI full suite:                   ~1 minute     ████████
```

## Validation Commands

```bash
# Measure current state
time pytest tests/integration/test_output_quality.py -v

# Apply Solution 1, measure improvement
time pytest tests/integration/test_output_quality.py -v

# Test dev workflow
time pytest -m "not slow" -n auto

# Show durations
pytest --durations=20
```

## Related to RFC

This analysis directly supports the testing-strategy-enhancements-v2.md RFC:
- Validates the need for shared fixtures (Solution 1 is an immediate win)
- Demonstrates value of test roots (replace showcase with minimal sites)
- Shows importance of proper fixture scoping (class vs function)
- Highlights need for marker discipline (`slow` marker)

**Key Insight**: The RFC's fixture strategy solves this exact problem systematically, but we can get quick wins NOW by fixing the most egregious cases.

## Action Items

- [ ] Apply Solution 1 (class-scoped fixture) - 5 min, high impact
- [ ] Apply Solution 2 (slow marker) - 2 min, medium impact  
- [ ] Apply Solution 3 (Hypothesis tuning) - 5 min, medium impact
- [ ] Measure and document improvements
- [ ] Update tests/README.md with fast dev workflow
- [ ] Proceed with RFC implementation for systematic solution
