# RFC: Version-Aware Taxonomies

**Status**: Draft  
**Created**: 2024-12-20  
**Author**: TBD  
**Related**: `plan-version-scoped-search.md`  
**Confidence**: 78% 🟡 (design solid, implementation details need verification)

## Executive Summary

Bengal's taxonomy system (tags, categories) currently collects pages from ALL versions into a single global index. When versioned docs exist, this creates confusing UX where clicking a "python" tag from v2 docs shows a mix of v1 and v2 content.

This RFC proposes **version-aware taxonomies** that:

1. **Maintain global tag indexes** (not fragmented per-version)
2. **Group posts by canonical identity** across versions
3. **Show version badges** indicating which versions have the content
4. **Default links to latest version** while enabling access to historical versions
5. **Cap displayed versions** at latest + 2 (configurable)

### Recommended approach

Single global `/tags/<tag>/` page that groups posts by canonical identity, with version badges and smart defaults. This avoids URL fragmentation while providing full version visibility.

## Problem Statement

### Current state (verified)

Taxonomy collection iterates over ALL pages without version filtering:

```python
# bengal/orchestration/taxonomy.py:248
for page in self.site.pages:  # ← All pages, all versions
    if not self._is_eligible_for_taxonomy(page):
        continue
    # ... collect tags
```

The `_is_eligible_for_taxonomy()` method only filters:
- Generated pages (`_generated` metadata)
- Autodoc pages (`content/api`, `content/cli`)

**No version filtering exists.**

Evidence: `bengal/orchestration/taxonomy.py:57-81`

### Impact

If versioned docs exist with the same tag:

```
content/_versions/v1/docs/tutorial.md  → tags: [python]
content/_versions/v2/docs/tutorial.md  → tags: [python]
```

Current behavior:
- Single `/tags/python/` page
- Lists BOTH v1 and v2 posts mixed together
- No indication which version a post belongs to
- Clicking any post could land on outdated content

### User expectations

Users browsing v2 documentation expect:
- Tag links to show v2-relevant content by default
- Visibility into what exists in other versions
- Clear indication when viewing historical content

## Design Options

### Option A: Version-fragmented taxonomies

```
/v1/tags/python/  → Only v1 posts
/v2/tags/python/  → Only v2 posts
/tags/python/     → Redirect to default version
```

**Pros:**
- Simple implementation (filter by version)
- Clear separation

**Cons:**
- URL fragmentation (SEO impact)
- Duplicated tag indexes
- No cross-version discovery
- More pages to generate and maintain

### Option B: Global index, version-scoped filtering (rejected)

```
/tags/python/           → Only default version posts
/tags/python/?v=v1      → Query param for other versions
```

**Pros:**
- Single URL per tag
- Explicit version selection

**Cons:**
- Static site can't do query param filtering
- Hidden content (v1 posts not visible by default)
- Poor discoverability

### Option C: Global index with version badges (recommended)

```
/tags/python/  → All posts, grouped by canonical ID, version badges
```

**Pros:**
- Full visibility of all content
- Single canonical URL per tag (good SEO)
- Defaults to latest (best content)
- Cross-version discovery
- Clean UX with version badges

**Cons:**
- More complex data model
- Requires canonical ID matching logic
- Template complexity

## Recommended Approach: Option C

### Data Model

#### Post grouping by canonical identity

Posts across versions are grouped by matching criteria:

```python
@dataclass
class CanonicalPost:
    """A post that may exist in multiple versions."""
    canonical_id: str  # Unique identifier across versions
    title: str  # Display title (from latest version)
    versions: dict[str, Page]  # version_id → Page
    default_page: Page  # Latest version (link target)

    @property
    def display_versions(self) -> list[str]:
        """Get versions to display (capped at max_shown)."""
        sorted_versions = sorted(self.versions.keys(), reverse=True)
        return sorted_versions[:self.max_shown]

    @property
    def overflow_count(self) -> int:
        """Number of older versions not shown."""
        return max(0, len(self.versions) - self.max_shown)
```

#### Canonical ID matching

Posts are matched across versions using (in priority order):

1. **Explicit frontmatter** (most reliable):
   ```yaml
   ---
   canonical_id: getting-started-python
   ---
   ```

2. **Relative path within version** (default):
   ```
   content/_versions/v1/docs/tutorial.md  → docs/tutorial
   content/_versions/v2/docs/tutorial.md  → docs/tutorial
   # Same relative path = same canonical ID
   ```

3. **Slug matching** (fallback, may have false positives):
   ```
   v1: slug: python-intro
   v2: slug: python-intro
   # Same slug = same canonical ID
   ```

#### Tag page metadata

```python
{
    "_posts": [
        CanonicalPost(
            canonical_id="getting-started-python",
            title="Getting Started with Python",
            versions={"v2": page_v2, "v1": page_v1},
            default_page=page_v2,
        ),
        # ...
    ],
    "_tag": "python",
    "_tag_slug": "python",
}
```

### Configuration

```yaml
# config.yaml
versioning:
  enabled: true
  versions: [v3, v2, v1]
  default: v3

taxonomies:
  version_aware: true  # Enable version-aware grouping
  version_badges:
    enabled: true
    max_shown: 3  # latest + 2
    show_overflow: true  # Show "+N older" indicator
```

### Template Usage

```jinja
{# templates/tag.html #}
<h1>Posts tagged "{{ tag.name }}"</h1>

{% for post in tag.posts %}
<article class="post-card">
  <a href="{{ post.default_page.url }}" class="post-title">
    {{ post.title }}
  </a>

  <div class="version-badges">
    {% for version in post.display_versions %}
      <a href="{{ post.versions[version].url }}"
         class="badge {% if version == site.default_version %}current{% endif %}">
        {{ version }}
      </a>
    {% endfor %}

    {% if post.overflow_count > 0 %}
      <span class="badge overflow" title="Available in {{ post.overflow_count }} older versions">
        +{{ post.overflow_count }}
      </span>
    {% endif %}
  </div>
</article>
{% endfor %}
```

### Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Posts tagged "python"                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Getting Started with Python           [v3] [v2] [v1]      │
│  ─────────────────────────────────────────────────────     │
│  Learn the basics of Python programming...                 │
│                                                             │
│  Advanced Async Patterns               [v3] [v2]           │
│  ─────────────────────────────────────────────────────     │
│  Deep dive into async/await...                             │
│                                                             │
│  Legacy Python 2.7 Migration                [v2] [v1]      │
│  ─────────────────────────────────────────────────────     │
│  How to migrate from Python 2.7...                         │
│                                                             │
│  Type Hints Deep Dive                  [v3]                │
│  ─────────────────────────────────────────────────────     │
│  New in v3: Comprehensive type hints...                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Badge styling:
  [v3] = Primary/current (solid background)
  [v2] = Secondary (outline)
  [v1] = Tertiary (muted)
  +N   = Overflow indicator (tooltip shows versions)
```

## Architecture Impact

### Modified Components

| Component | Change | Impact |
|-----------|--------|--------|
| `TaxonomyOrchestrator` | Add version grouping logic | Medium |
| `_is_eligible_for_taxonomy()` | No change (keep collecting all) | None |
| `_create_tag_pages()` | Group by canonical ID, create `CanonicalPost` | Medium |
| Tag templates | Add version badge rendering | Low |
| Theme CSS | Add badge styling | Low |

### New Components

| Component | Purpose |
|-----------|---------|
| `CanonicalPost` dataclass | Represents a post across versions |
| `canonical_id_resolver()` | Matches pages across versions |
| Version badge partial | Reusable template partial |

### Performance Considerations

- **Build time**: O(pages × versions) for canonical matching
- **Mitigation**: Cache canonical IDs during content discovery
- **Memory**: Slightly higher (grouping structure) but negligible

## Implementation Plan

### Phase 1: Core Data Model (1-2 hours)

1. Create `CanonicalPost` dataclass in `bengal/core/taxonomy.py`
2. Implement `canonical_id_resolver()` utility
3. Add `version_aware` config option

### Phase 2: Taxonomy Orchestrator (2-3 hours)

1. Modify `_create_tag_pages()` to group by canonical ID
2. Build version map for each canonical post
3. Determine default page (latest version)
4. Apply max_shown cap

### Phase 3: Templates (1-2 hours)

1. Create `partials/version-badges.html`
2. Update `tag.html` template
3. Add CSS for badge styling

### Phase 4: Testing (1-2 hours)

1. Unit tests for canonical ID resolution
2. Integration tests with versioned content
3. Template rendering tests

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| False positive canonical matches | Medium | Low | Use explicit `canonical_id` frontmatter for edge cases |
| Template complexity | Low | Low | Provide default badge partial in theme |
| Performance with many versions | Low | Low | Cap displayed versions, lazy load overflow |

## Alternatives Considered

### Why not version-scoped tags?

Fragmenting to `/v1/tags/`, `/v2/tags/`:
- Creates duplicate content for SEO
- Hides cross-version content
- More complex URL structure
- More pages to maintain

### Why not filter to default version only?

Showing only latest version in tags:
- Hides historical content
- Users can't discover what existed in v1
- Poor archival story

## Success Criteria

- [ ] Tag pages show posts grouped by canonical identity
- [ ] Version badges display correctly (latest + 2)
- [ ] Default links go to latest version
- [ ] Overflow indicator shows for 4+ version posts
- [ ] Performance impact < 5% of build time
- [ ] Backward compatible (works without versioning enabled)

## Confidence Scoring

| Component | Score | Reasoning |
|-----------|-------|-----------|
| Evidence (problem exists) | 38/40 | Verified: no version filtering in taxonomy code |
| Consistency (design coherent) | 25/30 | Solid design, some implementation details TBD |
| Recency | 15/15 | Current codebase analysis |
| Test coverage | 0/15 | Not yet implemented |
| **Total** | **78/100** 🟡 | |

## Open Questions

1. **Canonical ID storage**: Should we cache canonical IDs in build cache for incremental builds?
2. **Category support**: Apply same pattern to categories?
3. **RSS feeds**: Should tag RSS feeds be version-scoped or global?
4. **Search integration**: How does this interact with version-scoped search?

## Related Documents

- `plan-version-scoped-search.md` - Search filtering by version
- `rfc-url-ownership-architecture.md` - URL collision prevention


