# Plan: Sitemap Hreflang O(n²) to O(n) Optimization

**RFC**: `rfc-sitemap-hreflang-optimization.md`
**Status**: Draft
**Created**: 2025-12-21
**Estimated Time**: 45 minutes

---

## Summary

Optimize the sitemap generator's hreflang processing by pre-building a translation key index. This reduces complexity from O(n²) to O(n) for sites with `translation_key` pages, with no impact on non-i18n sites.

---

## Tasks

### Phase 1: Implementation

#### Task 1.1: Add translation index building to SitemapGenerator.generate()

- **Files**: `bengal/postprocess/sitemap.py`
- **Action**: Add translation index construction at the start of the `generate()` method, before the main page loop
- **Changes**:
  1. Add translation index dict initialization after the early return check (line ~95)
  2. Build index by iterating through `self.site.pages` once
  3. Store pages grouped by `translation_key`
- **Code Location**: Lines 95-100 (after `self.logger.info("sitemap_generation_start"...)`)
- **Commit**: `postprocess(sitemap): add translation index for O(1) hreflang lookups`

**Implementation**:
```python
# Build translation index once: O(n)
translation_index: dict[str, list[Any]] = {}
for page in self.site.pages:
    key = getattr(page, "translation_key", None)
    if key:
        translation_index.setdefault(key, []).append(page)
```

---

#### Task 1.2: Replace inner loop with index lookup

- **Files**: `bengal/postprocess/sitemap.py`
- **Action**: Replace the O(n) inner loop scan with O(1) index lookup
- **Changes**:
  1. Locate hreflang processing block (lines 132-167)
  2. Replace `for p in self.site.pages:` with `for p in translation_index.get(key, []):`
  3. Remove redundant `translation_key` check (already filtered by index)
- **Code Location**: Line 138
- **Depends on**: Task 1.1
- **Commit**: `postprocess(sitemap): use translation index for O(n) hreflang processing`

**Before**:
```python
for p in self.site.pages:  # O(n) for EVERY translated page
    if getattr(p, "translation_key", None) == key and p.output_path:
```

**After**:
```python
for p in translation_index.get(key, []):  # O(1) lookup
    if p.output_path:
```

---

### Phase 2: Testing

#### Task 2.1: Add unit test for translation index building

- **Files**: `tests/unit/postprocess/test_sitemap_generator.py`
- **Action**: Add new test class `TestSitemapGeneratorTranslationIndex` with tests for index construction
- **Tests**:
  1. `test_builds_translation_index_from_pages` - Verify index correctly groups pages by translation_key
  2. `test_translation_index_excludes_pages_without_key` - Verify non-i18n pages are excluded from index
  3. `test_translation_index_empty_when_no_translations` - Verify empty dict for non-i18n sites
- **Commit**: `tests(postprocess): add translation index unit tests`

**Test Outline**:
```python
class TestSitemapGeneratorTranslationIndex:
    """Test translation index optimization for hreflang processing."""

    def test_builds_translation_index_from_pages(self, tmp_path: Path) -> None:
        """Test that translation index groups pages by translation_key."""
        # Create pages with same translation_key
        page_en = self._create_mock_page(translation_key="post-1", lang="en", ...)
        page_fr = self._create_mock_page(translation_key="post-1", lang="fr", ...)
        page_other = self._create_mock_page(translation_key="post-2", ...)

        # Build index (mimicking implementation)
        translation_index = {}
        for page in [page_en, page_fr, page_other]:
            key = getattr(page, "translation_key", None)
            if key:
                translation_index.setdefault(key, []).append(page)

        assert len(translation_index["post-1"]) == 2
        assert len(translation_index["post-2"]) == 1

    def test_translation_index_excludes_pages_without_key(self) -> None:
        """Test that pages without translation_key are not indexed."""
        page_with_key = MagicMock(translation_key="post-1")
        page_without_key = MagicMock(translation_key=None)

        translation_index = {}
        for page in [page_with_key, page_without_key]:
            key = getattr(page, "translation_key", None)
            if key:
                translation_index.setdefault(key, []).append(page)

        assert "post-1" in translation_index
        assert len(translation_index) == 1  # Only one key

    def test_translation_index_empty_when_no_translations(self) -> None:
        """Test that non-i18n sites have empty translation index."""
        page1 = MagicMock(translation_key=None)
        page2 = MagicMock(translation_key=None)

        translation_index = {}
        for page in [page1, page2]:
            key = getattr(page, "translation_key", None)
            if key:
                translation_index.setdefault(key, []).append(page)

        assert translation_index == {}
```

---

#### Task 2.2: Add integration test for hreflang output consistency

- **Files**: `tests/unit/postprocess/test_sitemap_generator.py`
- **Action**: Add test to verify hreflang output is identical to before (regression test)
- **Tests**:
  1. `test_hreflang_output_matches_expected` - Verify hreflang links are correct for translated pages
  2. `test_hreflang_includes_x_default` - Verify x-default is still added correctly
- **Depends on**: Task 2.1
- **Commit**: `tests(postprocess): add hreflang output regression tests`

---

### Phase 3: Validation

- [ ] Run unit tests: `pytest tests/unit/postprocess/test_sitemap_generator.py -v`
- [ ] Run full test suite: `pytest tests/ -n auto`
- [ ] Run linter: `ruff check bengal/postprocess/sitemap.py`
- [ ] Run type checker: `mypy bengal/postprocess/sitemap.py`
- [ ] Verify sitemap output is identical on test site with translations

---

## Implementation Notes

### Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| Time complexity | O(n × t) | O(n + t) |
| 500 pages, 200 translated | 100,000 iterations | 700 iterations |
| Memory overhead | None | Minimal (dict of references) |
| Non-i18n sites | No change | No change (empty dict) |

### Verification Steps

1. **Build test-basic root**: Should work unchanged (no translations)
2. **Build site with translations**: Sitemap should be byte-for-byte identical
3. **Performance**: For sites with translations, build time should decrease

---

## Changelog Entry

```markdown
### Changed

- **Sitemap**: Optimized hreflang processing from O(n²) to O(n) by pre-building translation key index (#XXX)
```

---

## Files Modified

| File | Action |
|------|--------|
| `bengal/postprocess/sitemap.py` | Add translation index, use in hreflang loop |
| `tests/unit/postprocess/test_sitemap_generator.py` | Add translation index and regression tests |

---

## Risk Mitigation

- **Behavioral change**: Verify with snapshot comparison of sitemap.xml output
- **Memory overhead**: Index stores references only (negligible)
- **Non-i18n sites**: Empty dict, no performance impact

---

## Success Criteria

- [ ] Sitemap output is byte-for-byte identical to before
- [ ] All existing sitemap tests pass
- [ ] New translation index tests pass
- [ ] Linter and type checker pass
- [ ] Performance improvement measurable on i18n test site
