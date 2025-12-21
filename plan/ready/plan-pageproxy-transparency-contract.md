# Plan: Close PageProxy transparency gaps for output formats

**RFC**: `plan/ready/rfc-pageproxy-transparency-contract.md`  
**Status**: Implemented ✅  
**Created**: 2025-12-21  
**Completed**: 2025-12-21  
**Priority**: P0 (Correctness)  
**Confidence**: 90% 🟢  

---

## Executive Summary

This plan implements the RFC to close the `PageProxy` transparency gap for output formats. The work is scoped to:
1. Add `plain_text` delegate to `PageProxy`
2. Add unit tests verifying the behavior
3. Extend integration tests to assert proxies are present during output format generation

**Total tasks**: 5  
**Estimated time**: 30-45 minutes  

---

## Tasks by Subsystem

### Phase 1: Core Implementation

#### Task 1.1: Add `PageProxy.plain_text` property
**File**: `bengal/core/page/proxy.py`  
**What**: Add `plain_text` property that delegates to full page (triggers `_ensure_loaded()`)  
**Where**: After existing lazy properties section (~line 388, after `parsed_ast`)  
**Evidence**: Similar pattern used for `content`, `rendered_html`, `parsed_ast` at lines 273-388  

```python
@property
def plain_text(self) -> str:
    """Get plain text content (lazy-loaded from full page)."""
    self._ensure_loaded()
    return self._full_page.plain_text if self._full_page else ""
```

**Commit**: `core(page): add PageProxy.plain_text delegate; triggers lazy load for output formats`

---

### Phase 2: Unit Tests

#### Task 2.1: Add test for `plain_text` exists and returns string
**File**: `tests/unit/core/test_page_proxy.py`  
**What**: Add test verifying `plain_text` exists on `PageProxy` and returns `str`  
**Where**: New test class `TestPageProxyPlainText` after existing test classes  
**Pattern**: Follow `TestPageProxyLazyLoading` pattern at lines 107-179  

```python
class TestPageProxyPlainText:
    """Tests for plain_text property (output formats contract)."""

    def test_proxy_plain_text_exists_and_returns_string(self, cached_metadata, page_loader):
        """Verify plain_text property exists and returns str."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        result = proxy.plain_text

        assert isinstance(result, str)

    def test_proxy_plain_text_triggers_lazy_load(self, cached_metadata, page_loader):
        """Verify accessing plain_text triggers lazy load."""
        proxy = PageProxy(
            source_path=Path("content/blog/post.md"),
            metadata=cached_metadata,
            loader=page_loader,
        )

        assert not proxy._lazy_loaded

        # Access plain_text (should trigger load)
        _ = proxy.plain_text

        assert proxy._lazy_loaded
```

**Commit**: `tests(core): add PageProxy.plain_text unit tests; verify existence and lazy-load behavior`

---

### Phase 3: Integration Tests

#### Task 3.1: Add helper to check for PageProxy presence
**File**: `tests/integration/test_incremental_output_formats.py`  
**What**: Add assertion that at least one `PageProxy` is present during incremental build output format generation  
**Where**: Extend `test_incremental_build_generates_index_json_with_pages` (lines 44-79)  
**Evidence**: This test already exercises incremental builds but doesn't verify proxies are present  

Add import and helper:
```python
from bengal.core.page import PageProxy
```

Extend the test to assert proxies are present after incremental build:
```python
@pytest.mark.bengal(testroot="test-basic")
def test_incremental_build_generates_index_json_with_pages(site, build_site):
    """Test that incremental build also generates index.json with populated pages array."""
    # First: Full build
    build_site(incremental=False)

    # ... existing assertions ...

    # Second: Incremental build (no changes)
    build_site(incremental=True)

    # CRITICAL: Verify at least one PageProxy is present (contract test)
    proxy_count = sum(1 for p in site.pages if isinstance(p, PageProxy))
    assert proxy_count > 0, (
        "Expected at least one PageProxy in site.pages during incremental build. "
        "This test should exercise the PageProxy transparency contract."
    )

    # ... rest of existing assertions ...
```

**Commit**: `tests(integration): assert PageProxy presence in incremental output formats test`

#### Task 3.2: Add dedicated proxy contract test
**File**: `tests/integration/test_incremental_output_formats.py`  
**What**: Add a new test that explicitly constructs a scenario with PageProxy and verifies output formats succeed  
**Where**: New test function after existing tests  

```python
@pytest.mark.bengal(testroot="test-basic")
def test_output_formats_succeed_with_pageproxy_in_pages(site, build_site):
    """
    Contract test: Output formats must succeed when site.pages contains PageProxy objects.

    This test ensures the PageProxy transparency contract is maintained.
    If PageProxy is missing required attributes (like plain_text), this test will fail.
    """
    # Full build first
    build_site(incremental=False)

    # Incremental build (creates PageProxy for unchanged pages)
    build_site(incremental=True)

    # Verify we have at least one proxy (precondition)
    proxy_count = sum(1 for p in site.pages if isinstance(p, PageProxy))
    assert proxy_count > 0, (
        "Test precondition failed: expected PageProxy in site.pages. "
        "Modify test-basic root or test setup to ensure incremental build has proxies."
    )

    # Verify output formats generated successfully
    index_path = site.output_dir / "index.json"
    assert index_path.exists(), "index.json should be generated with PageProxy in pages"

    # Verify index.json is valid JSON with pages
    import json
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert "pages" in data
    assert len(data["pages"]) > 0, "index.json pages array should not be empty"

    # Verify llm-full.txt if enabled
    llm_path = site.output_dir / "llm-full.txt"
    if llm_path.exists():
        content = llm_path.read_text(encoding="utf-8")
        assert len(content) > 0, "llm-full.txt should have content"
```

**Commit**: `tests(integration): add PageProxy output-formats contract test`

---

## Rollout Sequence

| Order | Task | Depends On | Commit Message |
|-------|------|------------|----------------|
| 1 | 1.1 | — | `core(page): add PageProxy.plain_text delegate; triggers lazy load for output formats` |
| 2 | 2.1 | 1.1 | `tests(core): add PageProxy.plain_text unit tests; verify existence and lazy-load behavior` |
| 3 | 3.1 | 1.1 | `tests(integration): assert PageProxy presence in incremental output formats test` |
| 4 | 3.2 | 3.1 | `tests(integration): add PageProxy output-formats contract test` |

---

## Verification Checklist

After completing all tasks:

- [x] Run unit tests: `pytest tests/unit/core/test_page_proxy.py -v`
- [x] Run integration tests: `pytest tests/integration/test_incremental_output_formats.py -v`
- [x] Run linter: `ruff check bengal/core/page/proxy.py`
- [x] Verify no type errors: `mypy bengal/core/page/proxy.py`

---

## Acceptance Criteria (from RFC)

- [x] `PageProxy` exposes `plain_text` suitable for output formats
- [x] At least one test fails if `PageProxy` is missing an attribute that current output formats read
- [x] Integration coverage proves output formats succeed with a mixed `Page`/`PageProxy` list

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `plain_text` triggers unnecessary I/O in incremental builds | Keep this RFC correctness-only; caching is a follow-up RFC |
| Contract stays implicit and drifts | Tests must be updated when output formats read new attributes (review friction) |
| Test root doesn't produce proxies | Add assertion as precondition; adjust test setup if needed |

---

## References

- RFC: `plan/ready/rfc-pageproxy-transparency-contract.md`
- PageProxy: `bengal/core/page/proxy.py:33-739`
- plain_text (Page): `bengal/core/page/content.py:116-145`
- Existing unit tests: `tests/unit/core/test_page_proxy.py`
- Existing integration tests: `tests/integration/test_incremental_output_formats.py`
