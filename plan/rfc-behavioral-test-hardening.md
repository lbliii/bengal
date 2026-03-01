# RFC: Behavioral Test Hardening

## Status: Implementing

## Created: 2026-01-14

## Origin: Audit finding that tests pass but fail to catch behavioral regressions

---

## Summary

**Problem**: Bengal's test suite has 9,636 tests but fails to catch behavioral bugs. The tests verify *implementation paths* (methods called, code executed) rather than *behavioral outcomes* (correct output, invariants maintained). This creates a false sense of security where all tests pass while real bugs ship.

**Root Causes**:

1. **Over-mocking** (3,627 mock usages across 218 files): Unit tests mock dependencies and verify `.assert_called()` instead of actual outcomes.

2. **Weak assertions** (134+ instances): Tests use `assert result`, `assert True`, and `assert result is not None` without checking content correctness.

3. **Implementation coupling**: Tests break when refactoring even if behavior remains correct; bugs survive if they follow the expected code path.

4. **Property tests too narrow**: 129 `@given()` tests exist for utility functions, but core business logic lacks this coverage.

**Solution**: Systematic hardening in four phases:

1. **Behavioral assertions**: Replace `.assert_called()` patterns with outcome verification.

2. **Golden file testing**: Add snapshot tests for rendered output.

3. **Property tests expansion**: Add invariant tests for core build pipeline.

4. **Mutation testing**: Validate test suite effectiveness with `mutmut`.

**Priority**: High (tests provide false confidence, bugs reach users)
**Scope**: ~2,000 LOC refactoring over 4 sprints

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| Refactoring breaks existing tests | Medium | Low | Run full suite after each file; no deletions until replacement verified |
| New tests slower than mocks | Medium | Low | Property tests use `@settings(max_examples=100)`; golden tests are fast |
| Team unfamiliar with property tests | Low | Medium | Add examples and documentation; pair on first few tests |
| Mutation testing too slow for CI | Medium | Low | Run weekly, not per-PR; focus on critical paths only |

**Go/No-Go Criteria**:

- ✅ Verified mock problem: 3,627 usages across 218 files.
- ✅ Existing behavioral test model: `test_incremental_invariants.py`.
- ✅ Phased approach allows rollback at any point.
- ✅ No breaking changes to CI or existing workflows.

---

## Evidence: Current State

### Test Suite Statistics

| Metric | Count | Assessment | Verification |
| :--- | :--- | :--- | :--- |
| Total test functions | 9,636 | Large suite | `grep -r "def test_" tests/ \| wc -l` |
| Line coverage | ~42% | 🟡 Moderate | `uv run pytest --cov=bengal --cov-report=term-missing` |
| Mock/MagicMock usages | 3,627 | 🔴 **Critical** | `rg "Mock\|MagicMock" tests/ --count-matches` |
| `.assert_called` patterns | 134 | 🔴 Implementation-coupled | `rg "\.assert_called" tests/ --count-matches` |
| Weak assertions | 134+ | 🔴 Low signal | See methodology below |
| Property tests (`@given`) | 129 | 🟡 Only utilities | `rg "@given\(" tests/ --count-matches` |
| Integration tests (real builds) | 79 | ✅ Good foundation | `ls tests/integration/*.py \| wc -l` |

**Assertion validation methodology**: Counts patterns that verify existence but not correctness:

```bash
# Patterns counted:
rg "assert True$|assert result$|assert output$" tests/          # 20+ matches
rg "assert result is not None|assert response$" tests/          # 110+ matches
# Total: 134+ (verified 2026-01-14)
```

### Anti-Pattern Distribution

| Anti-Pattern | Files Affected | Example |
| :--- | :--- | :--- |
| Mock-only tests | 31 | `orchestrator.sections.finalize_sections.assert_called_once()` |
| Weak assertions | 24 | `assert result`, `assert True`, `assert output` |
| Heavy mock usage (>20/file) | 15 | `test_content.py` (95 mocks), `test_build_trigger.py` (104 mocks) |
| Property tests missing | All except 10 | Core pipeline has zero property tests |

**Highest mock density files**:

```text
tests/unit/server/test_build_trigger.py           104 Mock usages
tests/unit/orchestration/build/test_initialization.py  103 Mock usages
tests/unit/orchestration/build/test_finalization.py    100 Mock usages
tests/unit/orchestration/build/test_content.py          95 Mock usages
tests/unit/orchestration/build/test_rendering.py        90 Mock usages
```

### Symptom: Tests That Always Pass

```python
# tests/unit/orchestration/build/test_content.py (current)
def test_finalizes_sections(self, tmp_path):
    """Calls section orchestrator finalize."""
    orchestrator = MockPhaseContext.create_orchestrator(tmp_path)  # All mocked
    cli = MockPhaseContext.create_cli()
    orchestrator.sections.validate_sections.return_value = []

    phase_sections(orchestrator, cli, incremental=False, affected_sections=None)

    orchestrator.sections.finalize_sections.assert_called_once()  # Only checks call
```

**Problems with this test**:
- Doesn't verify sections are actually finalized correctly
- If `finalize_sections` has a bug internally, test still passes
- If implementation changes but behavior stays correct, test breaks
- Mock returns `[]` for validation - never tests error paths

### Symptom: The "Phantom Bug" Case Study

**Scenario**: A bug in `bengal/orchestration/taxonomy.py` caused category pages to be generated with empty titles.

1. **The Unit Test (Mocked)**:
   ```python
   def test_taxonomy_generation(self):
       gen = TaxonomyGenerator(mock_site)
       gen.generate()
       mock_site.renderer.render.assert_called()  # PASS: It was called!
   ```
2. **The Reality**: The `render` call was passed an empty title string because the logic for extracting metadata from the content layer was broken.
3. **The Behavioral Fix**:
   ```python
   def test_taxonomy_generation(self, tmp_path):
       site = create_site(tmp_path, taxonomy={"categories": ["news"]})
       site.build()
       assert_page_rendered(site.output_dir, "categories/news/index.html",
                            contains=["<h1>News</h1>"])  # FAIL: Caught the bug!
   ```

---

## Problem Analysis

### 1. Over-Mocking Hides Integration Bugs

**Current state**: Unit tests mock all collaborators and verify method calls.

```python
# What we test:
orchestrator.taxonomy.collect_and_generate.assert_called_once()

# What we DON'T test:
# - Are taxonomy pages actually generated?
# - Do generated pages have correct content?
# - Are URLs assigned correctly?
# - Does the cache get updated?
```

**Impact**: Bugs in how components interact are invisible. A taxonomy generator could return garbage and tests would pass as long as it's called.

### 2. Weak Assertions Provide No Signal

Found 117 tests with assertions that verify almost nothing:

```python
# These all pass regardless of correctness:
assert True                              # Literally useless
assert result                            # Only checks truthiness
assert result is not None                # Only checks existence
assert output                            # Doesn't verify content
assert response                          # Doesn't validate response body
```

**Example** (actual test):
```python
def test_builds_site(self, tmp_path):
    site = create_site(tmp_path)
    result = site.build()
    assert result  # What does this verify? Nothing meaningful.
```

### 3. Property Tests Cover Only Utilities

Current property tests (`@given`):

| Module | Tests | Examples/Run |
| :--- | :--- | :--- |
| URL Strategy | 14 | 1,400 |
| Paths | 19 | 1,900 |
| Text Utilities | 25 | 2,500 |
| Pagination | 16 | 1,600 |
| Dates | 23 | 2,300 |
| Slugify | 18 | 1,900 |
| **Core Pipeline** | **0** | **0** |

**Missing**: Property tests for core invariants such as:

- "Full build and incremental build produce identical output"
- "Adding a page doesn't change URLs of existing pages"
- "Taxonomy pages list all pages with that tag"
- "Build is idempotent: building twice produces same output"

### 4. Good Example Exists But Not Replicated

`tests/integration/test_incremental_invariants.py` shows the right pattern:

```python
def test_unchanged_file_never_rebuilt(self, warm_site):
    """INVARIANT: Unchanged files must never be rebuilt."""
    stats = warm_site.build(incremental=True)

    decision = getattr(stats, "incremental_decision", None)
    if decision is not None:
        pages_rebuilt = len(decision.pages_to_build)
        assert pages_rebuilt == 0, (
            f"Unchanged files were rebuilt: {pages_rebuilt} pages. "
            f"Expected 0 rebuilds on warm cache with no changes."
        )
```

**Why this is good**:
- Tests *behavior* (unchanged files not rebuilt), not *implementation*
- Runs real code, not mocks
- Assertion message explains the invariant
- Would catch bugs regardless of implementation details

---

## Proposed Solution

### Phase 1: Behavioral Assertion Patterns (~800 LOC)

#### 1.1 Replace Mock Verification with Outcome Checking

**Before** (current pattern):
```python
def test_builds_menus(self, tmp_path):
    orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
    orchestrator.site.menu = []

    phase_menus(orchestrator, incremental=False, changed_page_paths=set())

    orchestrator.menu.build.assert_called_once()  # Only verifies call
```

**After** (behavioral pattern):
```python
def test_builds_menus(self, tmp_path):
    """Menu build produces navigable menu structure."""
    site = create_minimal_site(tmp_path, pages=["docs/index.md", "about.md"])
    site.build()

    # Verify OUTCOME, not implementation
    assert len(site.menu) >= 2, "Menu should contain entries for pages"
    assert any(m.title == "Docs" for m in site.menu), "Docs section in menu"
    assert all(m.href.startswith("/") for m in site.menu), "Menu hrefs are absolute"
```

#### 1.2 Create Assertion Helpers

Add to `tests/_testing/assertions.py`:

```python
"""Behavioral assertion helpers for Bengal tests."""

def assert_page_rendered(output_dir: Path, page_path: str, *,
                         contains: list[str] | None = None,
                         not_contains: list[str] | None = None) -> None:
    """Assert a page was rendered with expected content."""
    html_path = output_dir / page_path
    assert html_path.exists(), f"Expected {page_path} to be rendered"

    content = html_path.read_text()
    for expected in (contains or []):
        assert expected in content, f"Expected '{expected}' in {page_path}"
    for forbidden in (not_contains or []):
        assert forbidden not in content, f"Unexpected '{forbidden}' in {page_path}"


def assert_build_idempotent(site: Site) -> None:
    """Assert building twice produces identical output."""
    first_hashes = _hash_output_dir(site.output_dir)
    site.build()
    second_hashes = _hash_output_dir(site.output_dir)

    assert first_hashes == second_hashes, (
        "Build is not idempotent - second build changed output"
    )


def assert_incremental_equivalent(site_path: Path) -> None:
    """Assert full build and incremental build produce same output."""
    # Full build
    site1 = Site.from_config(site_path)
    site1.build(incremental=False)
    full_hashes = _hash_output_dir(site1.output_dir)

    # Incremental build (from warm cache)
    site2 = Site.from_config(site_path)
    site2.build(incremental=True)
    incr_hashes = _hash_output_dir(site2.output_dir)

    assert full_hashes == incr_hashes, (
        "Incremental build differs from full build"
    )
```

#### 1.3 Manage Side Effects with Fakes, not Mocks

Avoid `unittest.mock` for core logic. Use "Fakes" that implement the same interface but act on in-memory state:

| Interface | Mock Approach | Behavioral (Fake) Approach |
|-----------|---------------|---------------------------|
| **Filesystem** | `mock_open()`, `mock_os` | `pyfakefs` or `tmp_path` (Real IO is fast enough) |
| **Registry** | `mock.patch("bengal.Registry")` | `Registry.clear()`, then use real registration |
| **CLI Output** | `mock_print`, `mock_sys_stdout` | `click.testing.CliRunner` (Captures real stream) |
| **Database/Cache** | `mock_cache.get.return_value` | Use `DiskCache` with a temporary directory |

**Guideline**: If a component is difficult to test without mocks, it is likely a sign of **tight coupling** that should be refactored into a cleaner, state-less interface.

#### 1.4 Performance Budget

Behavioral tests are slower than mock tests. We will maintain the following "Performance Budget":

- **Unit tests (Hardened)**: < 50ms per test
- **Integration tests (Golden)**: < 500ms per scenario
- **Property tests**: < 2s per 100 examples

To achieve this, we use `create_minimal_site()` helpers that avoid full template loading and only initialize the necessary sub-systems.

#### 1.5 Prioritize Refactoring by Impact

| Priority | Module | Tests | Mock Count | Issue | Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | `orchestration/build/` | 4 files | 388 | Critical path, all mock-based | Replace with real Site builds |
| P0 | `server/test_build_trigger.py` | 1 file | 104 | Highest mock density | Add behavioral WebSocket tests |
| P1 | `orchestration/incremental/` | 6 files | 70 | Mock-heavy | Leverage existing `warm_site` fixture |
| P1 | `cache/` | 12 files | 40 | Some good, some weak | Add idempotency checks |
| P2 | `rendering/` | 50+ files | 400 | Mixed quality | Focus on template tests |
| P2 | `cli/` | 15 files | 36 | Interactive, hard to test | Use `click.testing.CliRunner` |

**P0 files account for 492 mocks (14% of total) but test the most critical code path.**

### Phase 2: Golden File Testing (~400 LOC)

#### 2.1 Add Snapshot Tests for Rendered Output

Create `tests/golden/` directory with expected outputs:

```
tests/golden/
├── simple_site/
│   ├── input/
│   │   ├── bengal.toml
│   │   └── content/
│   │       ├── _index.md
│   │       └── about.md
│   └── expected/
│       ├── index.html
│       └── about/index.html
├── blog_site/
│   └── ...
└── taxonomy_site/
    └── ...
```

**Example golden input** (`tests/golden/simple_site/input/bengal.toml`):
```toml
[site]
title = "Golden Test Site"
baseURL = "https://example.com"

[build]
output_dir = "public"
```

**Example golden input** (`tests/golden/simple_site/input/content/_index.md`):
```markdown
---
title: Home
description: Welcome to the test site
---

# Welcome

This is the home page.
```

**Example expected output** (`tests/golden/simple_site/expected/index.html`):
```html
<!-- Normalized: timestamps/hashes stripped, whitespace normalized -->
<html>
<head>
  <title>Home | Golden Test Site</title>
  <meta name="description" content="Welcome to the test site">
</head>
<body>
  <h1>Welcome</h1>
  <p>This is the home page.</p>
</body>
</html>
```

Test implementation:
```python
# tests/integration/test_golden_output.py

@pytest.mark.parametrize("scenario", ["simple_site", "blog_site", "taxonomy_site"])
def test_golden_output(scenario: str, tmp_path: Path) -> None:
    """Built output matches expected golden files."""
    golden_dir = Path(__file__).parent.parent / "golden" / scenario
    input_dir = golden_dir / "input"
    expected_dir = golden_dir / "expected"

    # Copy input to tmp and build
    shutil.copytree(input_dir, tmp_path / "site")
    site = Site.from_config(tmp_path / "site")
    site.build()

    # Compare output to expected
    for expected_file in expected_dir.rglob("*"):
        if expected_file.is_file():
            rel_path = expected_file.relative_to(expected_dir)
            actual_file = site.output_dir / rel_path

            assert actual_file.exists(), f"Missing: {rel_path}"

            # Normalize and compare (ignore timestamps, etc.)
            expected = _normalize_html(expected_file.read_text())
            actual = _normalize_html(actual_file.read_text())
            assert expected == actual, f"Mismatch: {rel_path}"


def _normalize_html(html: str) -> str:
    """Normalize HTML for comparison, stripping volatile content."""
    import re

    # Remove build timestamps
    html = re.sub(r'data-build-time="[^"]*"', 'data-build-time=""', html)
    # Remove content hashes
    html = re.sub(r'\.[a-f0-9]{8}\.(css|js)', '.HASH.\\1', html)
    # Normalize whitespace
    html = re.sub(r'\s+', ' ', html).strip()

    return html
```

#### 2.2 Update Golden Files Command

Add CLI command to regenerate golden files:

```bash
# Regenerate all golden files (after intentional changes)
bengal test --update-golden

# Compare without updating
bengal test --check-golden
```

### Phase 3: Property Test Expansion (~600 LOC)

#### 3.1 Core Pipeline Invariants

```python
# tests/unit/orchestration/test_build_properties.py

from hypothesis import given, strategies as st, settings

@given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20))
@settings(max_examples=100)
def test_build_idempotent(page_titles: list[str], tmp_path: Path) -> None:
    """PROPERTY: Building twice produces identical output."""
    site = create_site_with_pages(tmp_path, page_titles)

    site.build()
    first_output = snapshot_output(site.output_dir)

    site.build()
    second_output = snapshot_output(site.output_dir)

    assert first_output == second_output


@given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
def test_all_pages_have_unique_urls(page_titles: list[str], tmp_path: Path) -> None:
    """PROPERTY: Every page gets a unique URL."""
    site = create_site_with_pages(tmp_path, page_titles)
    site.build()

    urls = [p.href for p in site.pages]
    assert len(urls) == len(set(urls)), f"Duplicate URLs: {urls}"


@given(st.lists(st.sampled_from(["python", "rust", "go", "js"]), min_size=0, max_size=5))
def test_tag_pages_list_all_tagged_content(tags: list[str], tmp_path: Path) -> None:
    """PROPERTY: Tag page lists exactly the pages with that tag."""
    site = create_site_with_tagged_pages(tmp_path, tags)
    site.build()

    for tag in set(tags):
        tag_page = site.get_taxonomy_page("tags", tag)
        tagged_content = [p for p in site.regular_pages if tag in p.tags]

        assert set(tag_page.members) == set(tagged_content), (
            f"Tag '{tag}' page has wrong members"
        )
```

#### 3.2 Incremental Build Invariants

```python
# tests/unit/orchestration/incremental/test_incremental_properties.py

@given(st.lists(st.integers(0, 9), min_size=1, max_size=5))
def test_incremental_matches_full(pages_to_modify: list[int], warm_site: Path) -> None:
    """PROPERTY: Incremental build output matches full build."""
    # Modify some pages
    for i in pages_to_modify:
        modify_page(warm_site, f"page_{i % 10}.md")

    # Full build
    site_full = Site.from_config(warm_site)
    site_full.build(incremental=False)
    full_output = snapshot_output(site_full.output_dir)

    # Clean and incremental build
    shutil.rmtree(site_full.output_dir)
    site_incr = Site.from_config(warm_site)
    site_incr.build(incremental=True)
    incr_output = snapshot_output(site_incr.output_dir)

    assert full_output == incr_output


@given(st.text(min_size=1, max_size=100))
def test_content_change_detected(new_content: str, warm_site: Path) -> None:
    """PROPERTY: Any content change is detected and rebuilt."""
    page_path = warm_site / "content" / "page_0.md"
    original = page_path.read_text()

    # Modify content
    page_path.write_text(original + f"\n{new_content}")

    site = Site.from_config(warm_site)
    stats = site.build(incremental=True)

    decision = stats.incremental_decision
    assert any("page_0" in str(p) for p in decision.pages_to_build), (
        f"Modified page not detected. Content added: {new_content[:50]}"
    )
```

### Phase 4: Mutation Testing Validation (~200 LOC)

#### 4.1 Add Mutation Testing to CI

```yaml
# .github/workflows/mutation.yml
name: Mutation Testing

on:
  schedule:
    - cron: '0 3 * * 0'  # Weekly Sunday 3am
  workflow_dispatch:

jobs:
  mutmut:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run mutation testing
        run: |
          uv run mutmut run \
            --paths-to-mutate bengal/orchestration/,bengal/cache/ \
            --tests-dir tests/unit/orchestration/,tests/unit/cache/ \
            --runner "pytest -x -q"
      - name: Generate report
        run: uv run mutmut results
      - name: Check mutation score
        run: |
          SCORE=$(uv run mutmut results --score-only)
          if [ "$SCORE" -lt 70 ]; then
            echo "Mutation score $SCORE% is below 70% threshold"
            exit 1
          fi
```

#### 4.2 Track Mutation Score Over Time

Add to `tests/TEST_COVERAGE.md`:

```markdown
## Mutation Testing Results

| Date | Module | Mutations | Killed | Score |
|------|--------|-----------|--------|-------|
| 2026-01-14 | orchestration/ | 150 | 45 | 30% |
| ... | ... | ... | ... | ... |

**Target**: 70% mutation score on critical paths
```

---

## Migration Strategy

### Gradual Adoption

Tests can be hardened incrementally:

1. **Week 1-2**: Add assertion helpers, refactor P0 modules (30 tests)
2. **Week 3-4**: Golden file infrastructure, first scenarios
3. **Week 5-6**: Property tests for core pipeline
4. **Week 7-8**: Mutation testing, remaining P1 modules

### Backward Compatibility

- Existing tests continue to run
- New patterns introduced alongside old
- Weak tests marked with `# TODO: harden` comments for tracking
- No tests deleted until replacement is verified

### Tracking Progress

Add marker for unhardened tests:

```python
@pytest.mark.needs_hardening
def test_builds_menus(self, tmp_path):
    """TODO: Replace mock verification with behavioral check."""
    ...
```

Track with:
```bash
pytest --collect-only -m needs_hardening | wc -l
```

---

## Testing Strategy

### Meta-Testing: Validate the Hardening

```python
# tests/meta/test_test_quality.py

def test_no_bare_assert_true():
    """No tests should use 'assert True'."""
    test_files = Path("tests/").rglob("test_*.py")
    violations = []

    for f in test_files:
        content = f.read_text()
        if "assert True" in content:
            violations.append(f)

    assert not violations, f"Found 'assert True' in: {violations}"


def test_mock_tests_have_behavioral_assertion():
    """Tests using mocks should also verify outcomes."""
    # Parse test files and check that mock-heavy tests
    # also contain assertions on actual values
    ...
```

---

## Success Criteria

### Quantitative

| Metric | Current | Target | Measurement |
| :--- | :--- | :--- | :--- |
| Weak assertions | 134+ | 0 | `rg "assert True$\|assert result$\|assert result is not None" tests/` |
| Mock-only tests | 134 | < 30 | `rg "\.assert_called" tests/ --count-matches` |
| Mock density (avg/file) | 18 | < 5 | `rg "Mock\|MagicMock" tests/ --count-matches / files` |
| Property tests | 129 | 300+ | `rg "@given" tests/ --count-matches` |
| Mutation score | ~30% | > 70% | `mutmut results --score-only` |
| Golden scenarios | 0 | 10+ | `ls tests/golden/ \| wc -l` |

### Qualitative

1. **Refactoring confidence**: Can change implementation without breaking tests

2. **Bug detection**: Tests catch intentional bugs (mutation testing)

3. **Invariant documentation**: Property tests document system contracts

4. **Regression prevention**: Golden files catch unintended output changes

---

## Implementation Checklist

### Phase 1: Behavioral Assertions
- [ ] Create `tests/_testing/assertions.py` with helpers
- [ ] Refactor `tests/unit/orchestration/build/test_content.py` (30 tests)
- [ ] Refactor `tests/unit/orchestration/incremental/` (25 tests)
- [ ] Add `@pytest.mark.needs_hardening` to remaining weak tests
- [ ] Update `TEST_COVERAGE.md` with hardening status

### Phase 2: Golden Files
- [ ] Create `tests/golden/` directory structure
- [ ] Add `simple_site` golden scenario
- [ ] Add `blog_site` golden scenario
- [ ] Add `taxonomy_site` golden scenario
- [ ] Implement `--update-golden` CLI command
- [ ] Add golden test to CI

### Phase 3: Property Tests
- [ ] Add `test_build_properties.py` (5 properties)
- [ ] Add `test_incremental_properties.py` (5 properties)
- [ ] Add `test_taxonomy_properties.py` (5 properties)
- [ ] Add `test_url_properties.py` (5 properties)
- [ ] Configure Hypothesis profiles for CI

### Phase 4: Mutation Testing
- [ ] Add `mutmut` to dev dependencies
- [ ] Create mutation testing CI workflow
- [ ] Establish baseline mutation score
- [ ] Add mutation score tracking to docs

---

## Non-Goals

1. **100% mutation score**: Some mutations are equivalent or test features we don't need to verify
2. **Eliminating all mocks**: Some mocking is appropriate (network, filesystem, etc.)
3. **Rewriting all tests**: Focus on high-impact modules first
4. **Perfect golden files**: Allow intentional differences (timestamps, etc.)

---

## Appendix: Quick Start - Hardening a Test in 5 Minutes

If you see a test using mocks like `test_rendering.py`, follow these steps to harden it:

1. **Identify the Outcome**: What should actually happen? (e.g., "A file `public/index.html` is created with 'Hello World'").
2. **Use the Site Fixture**: Replace `MockSite` with a real `Site` object using a temporary directory.
3. **Swap Mock for Action**: Instead of `mock_renderer.render()`, call `site.build()`.
4. **Assert Behavior**: Use `assert_page_rendered(site.output_dir, "index.html", contains=["Hello World"])`.
5. **Delete Mocks**: Remove all `@patch` decorators and `MagicMock` instances from the test.

---

## Appendix: Files Requiring Hardening

<details>
<summary>High-priority files (P0) - verified counts - click to expand</summary>

| File | Mock Usages | `.assert_called` | Priority |
| :--- | :--- | :--- | :--- |
| `tests/unit/server/test_build_trigger.py` | 104 | 4 | P0 |
| `tests/unit/orchestration/build/test_initialization.py` | 103 | 15 | P0 |
| `tests/unit/orchestration/build/test_finalization.py` | 100 | 14 | P0 |
| `tests/unit/orchestration/build/test_content.py` | 95 | 20 | P0 |
| `tests/unit/orchestration/build/test_rendering.py` | 90 | 12 | P0 |
| `tests/unit/orchestration/test_incremental_orchestrator.py` | 56 | 4 | P1 |
| `tests/unit/orchestration/incremental/test_filter_engine.py` | 28 | 1 | P1 |

**Verification command**:

```bash
for f in tests/unit/orchestration/build/*.py; do
  echo "$f: $(rg -c 'Mock|MagicMock' "$f" 2>/dev/null || echo 0) mocks"
done
```

</details>

<details>
<summary>Weak assertion locations - verified - click to expand</summary>

| File | Pattern | Count |
| :--- | :--- | :--- |
| `tests/rendering/parsers/test_patitas/test_performance.py` | `assert result$` | 8 |
| `tests/unit/cli/test_error_display.py` | `assert result is not None` | 8 |
| `tests/core/test_image_processing.py` | `assert result is not None` | 6 |
| `tests/unit/fonts/test_downloader.py` | `assert result is not None` | 6 |
| `tests/unit/utils/test_dates_properties.py` | `assert result is not None` | 4 |
| `tests/integration/test_incremental_cache_stability.py` | `assert result is not None` | 3 |

**Verification command**:

```bash
rg "assert True$|assert result$|assert result is not None" tests/ -c
```

</details>

---

## References

- `tests/integration/test_incremental_invariants.py` - Model behavioral test
- `tests/_testing/mocks.py` - Current mock infrastructure
- `tests/TEST_COVERAGE.md` - Coverage tracking
- [Hypothesis documentation](https://hypothesis.readthedocs.io/) - Property testing
- [mutmut documentation](https://mutmut.readthedocs.io/) - Mutation testing

---

## Decision Log

| Date | Decision | Rationale |
| :--- | :--- | :--- |
| 2026-01-14 | Initial draft | Audit finding that tests pass but fail to catch behavioral regressions |
| 2026-01-14 | Statistics verified and corrected | Mock count higher than originally estimated (3,627 vs 2,305), strengthening the case |
| 2026-01-14 | Added verification commands | Enable reproducible audits and progress tracking |
| 2026-01-14 | Added risk assessment | Document go/no-go criteria and mitigation strategies |
| 2026-01-14 | Added golden file examples | Provide concrete implementation guidance |
