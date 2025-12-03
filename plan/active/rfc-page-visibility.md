# RFC: Page Visibility System

**Status**: Draft  
**Created**: 2024-12-03  
**Author**: AI Assistant  
**Scope**: Core frontmatter, rendering, sitemap, SEO

---

## Summary

Add a unified page visibility system to Bengal with ergonomic defaults and granular overrides. Most users need one switch (`hidden: true`), power users get fine-grained control.

---

## Problem Statement

### Current State

Bengal has fragmented visibility controls:

| Option | Effect | Limitation |
|--------|--------|------------|
| `draft: true` | Excludes from production builds | All-or-nothing, can't access via URL |
| `menu: false` | Hides from navigation | Still in listings, sitemap, indexed |

### User Needs Not Met

1. **Unlisted pages** - Render but don't advertise (like unlisted YouTube videos)
2. **Internal docs** - Accessible but not indexed by search engines
3. **Staging content** - Visible in dev, hidden in production
4. **Archive pages** - Accessible but excluded from "recent posts" listings

### Competitor Analysis

| SSG | Strengths | Weaknesses |
|-----|-----------|------------|
| **Hugo** | Granular `_build` options | Complex, 3 nested fields |
| **Eleventy** | Simple `eleventyExcludeFromCollections` | Only handles listings |
| **Jekyll** | `published: false` | Binary, no middle ground |
| **Astro** | Collections are opt-in | Manual everything else |

**Gap**: No SSG offers a single ergonomic option that "just works" for the common "unlisted" case.

---

## Proposal

### Design Principles

1. **One option for 90% of cases** - `hidden: true` does everything
2. **Granular when needed** - Override individual behaviors
3. **Environment-aware** - Different behavior in dev vs production
4. **Explicit over implicit** - Clear what each option does

### The `hidden` Shorthand

```yaml
---
title: Secret Page
hidden: true
---
```

**Effect:**
- Excluded from navigation menus
- Excluded from `site.pages` (won't appear in listings/queries)
- Excluded from sitemap.xml
- Adds `<meta name="robots" content="noindex, nofollow">`
- Still renders and accessible via direct URL
- Still appears in dev server with visual indicator

### The `visibility` Object (Granular Control)

For power users who need fine-grained control:

```yaml
---
title: Partially Hidden Page
visibility:
  menu: false       # Hide from navigation (default: true)
  listings: false   # Hide from site.pages queries (default: true)
  sitemap: false    # Exclude from sitemap.xml (default: true)
  robots: noindex   # SEO directive (default: index)
  render: always    # always | never | local (default: always)
---
```

### Shorthand Expansion

`hidden: true` expands to:

```yaml
visibility:
  menu: false
  listings: false
  sitemap: false
  robots: noindex, nofollow
  render: always
```

### Environment-Aware Options

```yaml
---
title: WIP Feature Docs
visibility:
  render: local    # Only render in dev server, not production
---
```

| `render` value | Dev Server | Production Build |
|----------------|------------|------------------|
| `always` | Renders | Renders |
| `local` | Renders | Skipped |
| `never` | Skipped | Skipped |

### Combining with `draft`

`draft: true` remains separate - it means "not ready for any environment":

| State | Dev | Prod | Use Case |
|-------|-----|------|----------|
| `draft: true` | No (unless --drafts) | No | Work in progress |
| `hidden: true` | Yes (with indicator) | Yes (unlisted) | Unlisted content |
| `visibility.render: local` | Yes | No | Staging/preview |

---

## Implementation

### Phase 1: Core Support

**Files affected:**
- `bengal/core/page/metadata.py` - Add `hidden` and `visibility` properties
- `bengal/core/page/proxy.py` - Expose visibility in proxy

```python
@property
def hidden(self) -> bool:
    """Check if page is hidden (unlisted)."""
    return self.metadata.get("hidden", False)

@property
def visibility(self) -> dict:
    """Get visibility settings with defaults."""
    if self.hidden:
        return {
            "menu": False,
            "listings": False,
            "sitemap": False,
            "robots": "noindex, nofollow",
            "render": "always",
        }
    
    vis = self.metadata.get("visibility", {})
    return {
        "menu": vis.get("menu", True),
        "listings": vis.get("listings", True),
        "sitemap": vis.get("sitemap", True),
        "robots": vis.get("robots", "index, follow"),
        "render": vis.get("render", "always"),
    }
```

### Phase 2: Filter Integration

Update `site.pages` to respect visibility:

```python
@property
def pages(self) -> list[Page]:
    """Get all listable pages (respects visibility.listings)."""
    return [p for p in self._all_pages if p.in_listings]

@property
def all_pages(self) -> list[Page]:
    """Get ALL pages including hidden (for advanced queries)."""
    return self._all_pages
```

### Phase 3: Sitemap Integration

```python
def generate_sitemap(site: Site) -> str:
    """Generate sitemap.xml excluding hidden pages."""
    pages = [p for p in site.all_pages if p.in_sitemap]
```

### Phase 4: SEO Meta Tag

Auto-inject robots meta in base template:

```jinja2
<head>
  {% if page.robots_meta != 'index, follow' %}
  <meta name="robots" content="{{ page.robots_meta }}">
  {% endif %}
</head>
```

### Phase 5: Dev Server Visual Indicator

```css
body.hidden-page::before {
  content: "Hidden Page";
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  background: #f59e0b;
  color: white;
  padding: 4px 12px;
  font-size: 12px;
  z-index: 9999;
  border-radius: 0 0 4px 4px;
}
```

### Phase 6: Build-time Filtering

Respect `render: local` in production:

```python
def should_render(page: Page, is_production: bool) -> bool:
    render = page.visibility.get("render", "always")
    if render == "never":
        return False
    if render == "local" and is_production:
        return False
    return True
```

---

## Examples

### Example 1: Unlisted Page

```yaml
---
title: Secret Discount Page
hidden: true
---
```

Accessible at `/secret-discount/`, but won't appear in navigation, listings, sitemap, or search results.

### Example 2: Staging Documentation

```yaml
---
title: Upcoming Feature Docs
visibility:
  render: local
---
```

Visible during `bengal serve`, excluded from `bengal build`.

### Example 3: Archive Section

```yaml
---
title: Archive
visibility:
  listings: false  # Don't show in "recent posts"
  sitemap: true    # Keep in sitemap for SEO
  menu: true       # Keep in navigation
---
```

### Example 4: Internal Docs

```yaml
---
title: Internal API Notes
visibility:
  menu: false
  sitemap: false
  robots: noindex
  listings: true   # Still queryable for internal search
---
```

---

## Template Cheatsheet

```jinja2
{# Check if page is hidden #}
{% if page.hidden %}

{# Check specific visibility #}
{% if page.visibility.menu %}
{% if page.visibility.listings %}

{# Get robots directive #}
{{ page.robots_meta }}

{# Query including hidden pages #}
{% for p in site.all_pages %}

{# Query excluding hidden (default) #}
{% for p in site.pages %}
```

---

## Rollout Plan

| Phase | Scope | Timeline |
|-------|-------|----------|
| 1 | Core: `hidden` + `visibility` properties | Week 1 |
| 2 | Filters: `site.pages` vs `site.all_pages` | Week 1 |
| 3 | Sitemap: Exclude hidden pages | Week 1 |
| 4 | SEO: Auto robots meta tag | Week 2 |
| 5 | Navigation: Menu exclusion | Week 2 |
| 6 | Dev server: Visual indicator | Week 2 |
| 7 | Build: `render: local/never` support | Week 3 |
| 8 | Documentation + examples | Week 3 |

---

## Open Questions

1. **Should `hidden: true` also exclude from search index?** Yes
2. **CLI flag `--include-hidden` for debugging?** Yes
3. **Should `hidden` cascade to child pages?** No, explicit per-page
4. **RSS feed handling?** Exclude hidden, like sitemap

---

## Success Criteria

- [ ] `hidden: true` works as single switch for unlisted content
- [ ] `visibility` object allows granular overrides
- [ ] `site.pages` automatically excludes hidden
- [ ] Sitemap excludes hidden pages
- [ ] Robots meta injected for hidden pages
- [ ] Dev server shows visual indicator
- [ ] `render: local` works for staging content
- [ ] Zero breaking changes to existing sites

---

## Full Visibility Schema

```yaml
visibility:
  menu: true              # Include in navigation menus
  listings: true          # Include in site.pages queries
  sitemap: true           # Include in sitemap.xml
  robots: "index, follow" # Robots meta directive
  render: "always"        # always | local | never
  search: true            # Include in search index
  rss: true               # Include in RSS feeds
```

