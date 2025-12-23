# Plan: Template Convenience Functions for Blog & Content Sites

**RFC**: `rfc-template-conveniences.md`  
**Status**: Draft  
**Created**: 2025-12-23  
**Estimated Time**: 18-24 hours

---

## Summary

Implement template convenience functions, dataclasses, and page properties that simplify common blog and content site patterns. Adds Author support, date grouping helpers, series navigation, social sharing URLs, featured posts accessor, and section statistics.

---

## Tasks

### Phase 1: Date & Collection Helpers (2-3 hours)

Quick wins that provide immediate value with minimal complexity.

#### Task 1.1: Add date utility filters
- **Files**: `bengal/rendering/template_functions/dates.py`
- **Action**: Add `days_ago`, `months_ago`, `month_name`, `humanize_days` filters
- **Tests**: `tests/unit/rendering/template_functions/test_dates.py`
- **Commit**: `rendering(dates): add days_ago, months_ago, month_name, humanize_days filters`

#### Task 1.2: Add page age properties
- **Files**: `bengal/core/page/computed.py`
- **Action**: Add `age_days` and `age_months` properties to Page
- **Tests**: `tests/unit/core/test_page_age.py`
- **Commit**: `core(page): add age_days and age_months computed properties`

#### Task 1.3: Add collection grouping filters
- **Files**: `bengal/rendering/template_functions/collections.py`
- **Action**: Add `group_by_year`, `group_by_month`, `archive_years` filters
- **Tests**: `tests/unit/rendering/template_functions/test_collections.py`
- **Commit**: `rendering(collections): add group_by_year, group_by_month, archive_years filters`

#### Task 1.4: Register new date/collection filters
- **Files**: `bengal/rendering/template_functions/__init__.py`
- **Action**: Ensure new filters are registered in environment
- **Depends on**: Tasks 1.1, 1.3
- **Commit**: `rendering: register date and collection filters in template environment`

---

### Phase 2: Author Support (4-6 hours)

Structured author data with social links and template functions.

#### Task 2.1: Create Author dataclass
- **Files**: `bengal/core/author.py` (new)
- **Action**: Create Author dataclass with social links, `from_frontmatter()` factory, slug auto-generation
- **Tests**: `tests/unit/core/test_author.py` (new)
- **Commit**: `core: add Author dataclass with social links and from_frontmatter factory`

#### Task 2.2: Update AuthorIndex to extract structured metadata
- **Files**: `bengal/cache/indexes/author_index.py`
- **Action**: Update `extract_keys()` to capture all structured fields (email, bio, avatar, social links)
- **Tests**: `tests/unit/cache/indexes/test_author_index.py`
- **Commit**: `cache(indexes): update AuthorIndex to extract full structured author metadata`

#### Task 2.3: Add page.author and page.authors properties
- **Files**: `bengal/core/page/computed.py`
- **Action**: Add `author` (returns Author | None) and `authors` (returns list[Author]) properties
- **Depends on**: Task 2.1
- **Tests**: `tests/unit/core/test_page_author.py` (new)
- **Commit**: `core(page): add author and authors computed properties returning Author objects`

#### Task 2.4: Create author template functions module
- **Files**: `bengal/rendering/template_functions/authors.py` (new)
- **Action**: Create `author_url()`, `get_author()`, `author_posts()` functions with registration
- **Depends on**: Task 2.1
- **Tests**: `tests/unit/rendering/template_functions/test_authors.py` (new)
- **Commit**: `rendering: add author template functions (author_url, get_author, author_posts)`

#### Task 2.5: Add site.authors property
- **Files**: `bengal/core/site.py`
- **Action**: Add `authors` property returning `dict[str, Author]` with caching
- **Depends on**: Tasks 2.1, 2.2
- **Tests**: `tests/unit/core/test_site_authors.py` (new)
- **Commit**: `core(site): add authors property returning cached dict of Author objects`

#### Task 2.6: Register author template functions
- **Files**: `bengal/rendering/template_functions/__init__.py`
- **Action**: Register author functions module
- **Depends on**: Task 2.4
- **Commit**: `rendering: register author template functions module`

---

### Phase 3: Social Sharing URLs (2-3 hours)

Generate share URLs for Twitter, Facebook, LinkedIn, Reddit, HN, Email, Mastodon, Bluesky.

#### Task 3.1: Create share template functions module
- **Files**: `bengal/rendering/template_functions/share.py` (new)
- **Action**: Create `share_url()` function supporting all platforms, plus convenience functions
- **Tests**: `tests/unit/rendering/template_functions/test_share.py` (new)
- **Commit**: `rendering: add share_url template function for social sharing URLs`

#### Task 3.2: Register share template functions
- **Files**: `bengal/rendering/template_functions/__init__.py`
- **Action**: Register share functions module
- **Depends on**: Task 3.1
- **Commit**: `rendering: register share template functions module`

---

### Phase 4: Series Support (6-8 hours)

Multi-part content with automatic navigation.

#### Task 4.1: Create Series dataclass
- **Files**: `bengal/core/series.py` (new)
- **Action**: Create Series dataclass with auto-slug, `total` property, position/prev/next methods
- **Tests**: `tests/unit/core/test_series.py` (new)
- **Commit**: `core: add Series dataclass with position, prev/next navigation methods`

#### Task 4.2: Create SeriesIndex
- **Files**: `bengal/cache/indexes/series_index.py` (new)
- **Action**: Create QueryIndex subclass that extracts `series.name`, `series.part`, `series.description`
- **Tests**: `tests/unit/cache/indexes/test_series_index.py` (new)
- **Commit**: `cache(indexes): add SeriesIndex for O(1) series lookup`

#### Task 4.3: Register SeriesIndex in index registry
- **Files**: `bengal/cache/indexes/__init__.py`
- **Action**: Register SeriesIndex in available indexes
- **Depends on**: Task 4.2
- **Commit**: `cache(indexes): register SeriesIndex in index registry`

#### Task 4.4: Add page.series property
- **Files**: `bengal/core/page/computed.py`
- **Action**: Add `series` property that builds Series object from index with proper sorting
- **Depends on**: Tasks 4.1, 4.2
- **Tests**: `tests/unit/core/test_page_series.py` (new)
- **Commit**: `core(page): add series property with sorted parts from SeriesIndex`

#### Task 4.5: Add page series navigation properties
- **Files**: `bengal/core/page/computed.py`
- **Action**: Add `series_position`, `prev_in_series`, `next_in_series` properties
- **Depends on**: Task 4.4
- **Tests**: `tests/unit/core/test_page_series.py`
- **Commit**: `core(page): add series_position, prev_in_series, next_in_series properties`

---

### Phase 5: Featured Posts & Section Stats (2-3 hours)

Site-level featured posts and section statistics.

#### Task 5.1: Add site.featured_posts property
- **Files**: `bengal/core/site.py`
- **Action**: Add `featured_posts` property that returns pages with `featured: true` or `featured` tag
- **Tests**: `tests/unit/core/test_site_featured.py` (new)
- **Commit**: `core(site): add featured_posts property with caching`

#### Task 5.2: Add section statistics properties
- **Files**: `bengal/core/section.py`
- **Action**: Add `post_count`, `total_word_count`, `date_range`, `last_updated` properties
- **Tests**: `tests/unit/core/test_section_stats.py` (new)
- **Commit**: `core(section): add post_count, total_word_count, date_range, last_updated properties`

---

### Phase 6: Integration Tests (2-3 hours)

Verify all features work together in realistic scenarios.

#### Task 6.1: Author pages integration test
- **Files**: `tests/integration/test_author_pages.py` (new)
- **Action**: Test author archive page generation with structured author data
- **Depends on**: Phase 2
- **Commit**: `tests(integration): add author pages end-to-end test`

#### Task 6.2: Series navigation integration test
- **Files**: `tests/integration/test_series_navigation.py` (new)
- **Action**: Test multi-part series with prev/next navigation
- **Depends on**: Phase 4
- **Commit**: `tests(integration): add series navigation end-to-end test`

#### Task 6.3: Archive grouping integration test
- **Files**: `tests/integration/test_archive_pages.py` (new)
- **Action**: Test group_by_year/month with archive template rendering
- **Depends on**: Phase 1
- **Commit**: `tests(integration): add archive page grouping end-to-end test`

---

### Phase 7: Validation

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Linter passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Health validators pass (`bengal health`)
- [ ] Documentation examples render correctly

---

## Task Dependencies

```
Phase 1: No dependencies (start here)
    ├── 1.1 → 1.4
    ├── 1.2 (independent)
    └── 1.3 → 1.4

Phase 2: No dependencies on other phases
    ├── 2.1 → 2.2, 2.3, 2.4, 2.5
    ├── 2.2 → 2.5
    ├── 2.3 (after 2.1)
    ├── 2.4 → 2.6
    └── 2.5 (after 2.1, 2.2)

Phase 3: No dependencies on other phases
    └── 3.1 → 3.2

Phase 4: No dependencies on other phases
    ├── 4.1 → 4.4, 4.5
    ├── 4.2 → 4.3, 4.4
    └── 4.4 → 4.5

Phase 5: No dependencies on other phases
    ├── 5.1 (independent)
    └── 5.2 (independent)

Phase 6: Integration tests
    ├── 6.1 (after Phase 2)
    ├── 6.2 (after Phase 4)
    └── 6.3 (after Phase 1)
```

---

## Parallel Execution Paths

For maximum efficiency, these can run in parallel:

**Path A**: Phase 1 (dates/collections) → Task 6.3  
**Path B**: Phase 2 (authors) → Task 6.1  
**Path C**: Phase 3 (sharing) - independent  
**Path D**: Phase 4 (series) → Task 6.2  
**Path E**: Phase 5 (featured/stats) - independent  

---

## Files Summary

### New Files (11)

| File | Purpose |
|------|---------|
| `bengal/core/author.py` | Author dataclass |
| `bengal/core/series.py` | Series dataclass |
| `bengal/cache/indexes/series_index.py` | SeriesIndex |
| `bengal/rendering/template_functions/share.py` | Social sharing URLs |
| `bengal/rendering/template_functions/authors.py` | Author template functions |
| `tests/unit/core/test_author.py` | Author tests |
| `tests/unit/core/test_series.py` | Series tests |
| `tests/unit/core/test_page_author.py` | Page author property tests |
| `tests/unit/core/test_page_series.py` | Page series property tests |
| `tests/unit/core/test_page_age.py` | Page age property tests |
| `tests/unit/core/test_site_authors.py` | Site authors tests |
| `tests/unit/core/test_site_featured.py` | Featured posts tests |
| `tests/unit/core/test_section_stats.py` | Section stats tests |
| `tests/unit/cache/indexes/test_series_index.py` | SeriesIndex tests |
| `tests/unit/rendering/template_functions/test_share.py` | Share URL tests |
| `tests/unit/rendering/template_functions/test_authors.py` | Author function tests |
| `tests/integration/test_author_pages.py` | Author integration |
| `tests/integration/test_series_navigation.py` | Series integration |
| `tests/integration/test_archive_pages.py` | Archive integration |

### Modified Files (7)

| File | Changes |
|------|---------|
| `bengal/core/page/computed.py` | Add author, authors, age_days, age_months, series, series_position, prev_in_series, next_in_series |
| `bengal/core/site.py` | Add featured_posts, authors properties |
| `bengal/core/section.py` | Add post_count, total_word_count, date_range, last_updated |
| `bengal/cache/indexes/author_index.py` | Update extract_keys for full metadata |
| `bengal/cache/indexes/__init__.py` | Register SeriesIndex |
| `bengal/rendering/template_functions/dates.py` | Add days_ago, months_ago, month_name, humanize_days |
| `bengal/rendering/template_functions/collections.py` | Add group_by_year, group_by_month, archive_years |
| `bengal/rendering/template_functions/__init__.py` | Register new modules |

---

## Changelog Entry

```markdown
### Added

- **Author support**: `Author` dataclass with social links, `page.author`/`page.authors` properties, `author_url()`, `get_author()`, `author_posts()` template functions, `site.authors` property
- **Series support**: `Series` dataclass, `SeriesIndex`, `page.series`, `page.series_position`, `page.prev_in_series`, `page.next_in_series` for multi-part content navigation
- **Date helpers**: `days_ago`, `months_ago`, `month_name`, `humanize_days` filters; `page.age_days`, `page.age_months` properties
- **Collection helpers**: `group_by_year`, `group_by_month`, `archive_years` filters for archive pages
- **Social sharing**: `share_url()` function for Twitter, Facebook, LinkedIn, Reddit, Hacker News, Email, Mastodon, Bluesky
- **Featured posts**: `site.featured_posts` property returning pages with `featured: true` or `featured` tag
- **Section statistics**: `section.post_count`, `section.total_word_count`, `section.date_range`, `section.last_updated` properties
```

---

## Implementation Notes

### Author Index Backward Compatibility

The `AuthorIndex.extract_keys()` changes are additive - existing string authors continue to work, structured authors get full metadata extracted.

### Series Sorting Logic

Series parts sorted by:
1. Numeric parts first (ascending)
2. String parts (e.g., "intro", "appendix")
3. Fallback to date for identical parts

### Cache Invalidation

- `site._authors_cache` cleared on site reload
- `site._featured_posts_cache` cleared on site reload
- `section._total_word_count_cache` is per-section

### No PageCore Changes

Author and series data remains in `page.metadata` - computed on access to avoid cache migration.

---

**Ready for implementation. Start with Phase 1 for quick wins.**
