# RFC: Page Redirects and Aliases

**Status**: Implemented ✅

## Summary

Add Hugo-style `aliases` support to Bengal, allowing pages to specify alternative URLs that redirect to their canonical location. This preserves SEO, maintains link stability during content reorganization, and provides a familiar pattern for writers migrating from Hugo.

## Goals

- Support `aliases: ["/old/url/", "/another/url/"]` frontmatter field
- Generate redirect HTML pages at each alias URL during build
- Include proper SEO signals (`<link rel="canonical">`, `<meta http-equiv="refresh">`)
- Optionally generate platform-specific redirect files (`_redirects` for Netlify, etc.)
- Maintain compatibility with incremental builds (aliases are cacheable)

## Non-Goals

- Server-side redirect configuration (Apache `.htaccess`, nginx)—out of scope for MVP
- Redirect status code control (301 vs 302)—use meta refresh for simplicity
- Redirect chains or loop detection—user responsibility for now
- External URL redirects (`redirect: https://example.com`)—separate RFC

## User Stories

1. **As a writer**, when I reorganize my blog from `/posts/2020/my-post/` to `/blog/my-post/`, I want old links to still work by adding an alias.

2. **As a migrator from Hugo**, I want to keep my existing `aliases` frontmatter working without changes.

3. **As an SEO-conscious site owner**, I want redirect pages to include proper canonical hints so search engines update their indexes.

4. **As a Netlify/Vercel user**, I want Bengal to optionally generate a `_redirects` file for faster server-side redirects.

---

## Design

### Frontmatter Syntax

```yaml
---
title: My New Post
slug: my-new-post
aliases:
  - /old/posts/my-post/
  - /2020/01/original-post/
  - /drafts/working-title/
---
```

**Semantics**:
- Each alias is an **absolute path** (starting with `/`)
- Aliases point **to** this page (not from this page)
- Multiple pages can have overlapping aliases → build warning

### PageCore Field Addition

Add `aliases` to `PageCore` for caching:

```python
# bengal/core/page/page_core.py
@dataclass
class PageCore(Cacheable):
    # ... existing fields ...

    # Redirect aliases (Hugo compatibility)
    aliases: list[str] = field(default_factory=list)  # Alternative URLs that redirect here
```

**Why cacheable?**
- Aliases come from frontmatter (static, not computed)
- Need to detect alias changes for incremental rebuilds
- JSON-serializable (list of strings)

### Redirect HTML Generation

New postprocessor: `RedirectGenerator`

```python
# bengal/postprocess/redirects.py
class RedirectGenerator:
    """
    Generates redirect HTML pages for page aliases.

    For each page with aliases, creates lightweight HTML files at the
    alias paths that redirect to the canonical URL.
    """

    def __init__(self, site: Site) -> None:
        self.site = site

    def generate(self) -> None:
        """Generate all redirect pages."""
        redirects_generated = 0

        for page in self.site.pages:
            for alias in page.aliases:
                if self._generate_redirect(alias, page.url):
                    redirects_generated += 1

        if redirects_generated > 0:
            logger.info("redirects_generated", count=redirects_generated)

    def _generate_redirect(self, from_path: str, to_url: str) -> bool:
        """Generate a single redirect HTML page."""
        # Normalize paths
        from_path = from_path.strip("/")
        output_path = self.site.output_dir / from_path / "index.html"

        # Check for conflicts
        if output_path.exists():
            logger.warning(
                "redirect_conflict",
                alias=from_path,
                target=to_url,
                reason="path already exists",
            )
            return False

        # Generate redirect HTML
        html = self._render_redirect_html(from_path, to_url)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return True

    def _render_redirect_html(self, from_path: str, to_url: str) -> str:
        """Render redirect HTML with SEO hints."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url={to_url}">
    <link rel="canonical" href="{to_url}">
    <title>Redirecting...</title>
    <meta name="robots" content="noindex">
</head>
<body>
    <p>This page has moved. Redirecting to <a href="{to_url}">{to_url}</a>...</p>
</body>
</html>'''
```

### Integration with Build Pipeline

Add to `SpecialPagesGenerator` or create standalone hook:

```python
# bengal/orchestration/build_orchestrator.py

def _run_postprocessing(self) -> None:
    """Run all postprocessing steps."""
    # ... existing postprocessors ...

    # Generate redirect pages
    from bengal.postprocess.redirects import RedirectGenerator
    redirect_gen = RedirectGenerator(self.site)
    redirect_gen.generate()
```

### Sitemap Integration

Redirect pages should NOT appear in sitemap (they're not real content). The canonical pages are already included.

### Optional: Platform-Specific Redirects

For Netlify/Vercel, generate a `_redirects` file for faster server-side handling:

```python
# bengal/postprocess/redirects.py

def generate_redirects_file(self) -> None:
    """Generate _redirects file for Netlify/Vercel."""
    if not self.site.config.get("redirects", {}).get("generate_redirects_file", False):
        return

    lines = []
    for page in self.site.pages:
        for alias in page.aliases:
            lines.append(f"{alias}  {page.url}  301")

    if lines:
        redirects_path = self.site.output_dir / "_redirects"
        redirects_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

**Configuration**:
```toml
# bengal.toml
[redirects]
generate_html = true           # Default: true
generate_redirects_file = true # For Netlify/Vercel (default: false)
```

---

## Implementation Plan

### Phase 1: Core Feature (MVP)

1. **Add `aliases` field to PageCore** (`bengal/core/page/page_core.py`)
   - Add field with `default_factory=list`
   - Add to `to_cache_dict()` and `from_cache_dict()`

2. **Add property delegates**
   - `Page.aliases` (`bengal/core/page/__init__.py`)
   - `PageProxy.aliases` (`bengal/core/page/proxy.py`)

3. **Create RedirectGenerator** (`bengal/postprocess/redirects.py`)
   - Generate redirect HTML pages
   - Log warnings for conflicts

4. **Integrate with build pipeline** (`bengal/orchestration/build_orchestrator.py`)
   - Call `RedirectGenerator.generate()` after page rendering

5. **Add tests**
   - Unit tests for redirect HTML generation
   - Integration test with test site

6. **Update documentation**
   - Fix `site/content/docs/guides/migrating-content.md` (currently aspirational)
   - Add to frontmatter reference

### Phase 2: Enhancements (Post-MVP)

1. **Generate `_redirects` file** for Netlify/Vercel
2. **Conflict detection** (multiple pages claiming same alias)
3. **Incremental build awareness** (regenerate redirects only when aliases change)
4. **Templated redirects** (use theme template if available)

---

## Files to Modify

| File | Change |
|------|--------|
| `bengal/core/page/page_core.py` | Add `aliases: list[str]` field |
| `bengal/core/page/__init__.py` | Add `aliases` property delegate |
| `bengal/core/page/proxy.py` | Add `aliases` property delegate |
| `bengal/postprocess/__init__.py` | Export `RedirectGenerator` |
| `bengal/postprocess/redirects.py` | **NEW** - Redirect page generator |
| `bengal/orchestration/build_orchestrator.py` | Call redirect generator |
| `site/content/docs/guides/migrating-content.md` | Fix documentation |
| `site/content/docs/reference/frontmatter.md` | Add `aliases` field docs |
| `tests/unit/postprocess/test_redirects.py` | **NEW** - Unit tests |
| `tests/integration/test_redirect_generation.py` | **NEW** - Integration tests |

---

## Testing Plan

### Unit Tests

```python
# tests/unit/postprocess/test_redirects.py

def test_redirect_html_structure():
    """Test redirect HTML has required elements."""
    gen = RedirectGenerator(mock_site)
    html = gen._render_redirect_html("/old/", "/new/")

    assert '<meta http-equiv="refresh"' in html
    assert 'url=/new/' in html
    assert '<link rel="canonical" href="/new/">' in html
    assert 'noindex' in html

def test_aliases_parsed_from_frontmatter():
    """Test aliases field parsed correctly."""
    page = parse_page("""
---
title: Test
aliases:
  - /old/path/
  - /another/
---
Content
""")
    assert page.aliases == ["/old/path/", "/another/"]

def test_redirect_conflict_warning(caplog):
    """Test warning when alias conflicts with existing page."""
    # Create page at /about/
    # Create another page with alias: ["/about/"]
    # Should log warning, not overwrite
```

### Integration Tests

```python
# tests/integration/test_redirect_generation.py

def test_redirects_generated_during_build(tmp_path):
    """Test redirect pages created during full build."""
    # Create test site with page having aliases
    # Run build
    # Verify redirect HTML files exist

def test_redirect_does_not_appear_in_sitemap(tmp_path):
    """Test redirect pages excluded from sitemap.xml."""
```

---

## Migration/Compatibility

### Hugo Compatibility

Bengal's `aliases` field matches Hugo's syntax exactly:

```yaml
# Works in both Hugo and Bengal
aliases:
  - /old/url/
  - /another/old/url/
```

### Breaking Changes

**None.** This is a purely additive feature.

### Documentation Updates

- Fix `migrating-content.md` which currently documents this as if it exists
- Add `aliases` to frontmatter reference with examples

---

## Alternatives Considered

### 1. `redirect` Field (Single Target)

```yaml
redirect: /new-url/
```

**Rejected**: This is the inverse semantic (page redirects TO target, not FROM aliases). Could add later as separate feature for redirect-only pages.

### 2. Separate `_redirects.yaml` File

```yaml
# content/_redirects.yaml
- from: /old/
  to: /new/
```

**Rejected**: Less ergonomic for writers. Hugo's pattern of co-locating aliases with content is more intuitive. Could add as optional supplement.

### 3. Server-Side Only

Only generate `_redirects` file, no HTML fallback.

**Rejected**: HTML fallback is essential for static hosts without redirect support (GitHub Pages, generic CDNs).

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Alias conflicts (two pages claim same path) | Log warning, skip conflicting redirect |
| Alias points to non-existent path | N/A—alias is the source, not target |
| Performance with many aliases | HTML generation is fast (~1ms per redirect) |
| Redirect loops | User responsibility; out of scope for MVP |
| Cache invalidation | Aliases in PageCore; cache detects frontmatter changes |

---

## Success Criteria

- [x] `aliases` field parsed from frontmatter
- [x] Redirect HTML generated at each alias path
- [x] Redirect HTML includes canonical link and noindex
- [x] No redirects appear in sitemap.xml (they're not real content)
- [x] Build logs redirect count
- [x] Conflicts logged as warnings
- [x] Tests cover happy path and edge cases
- [ ] Documentation updated
- [ ] Hugo migration guide accurate

---

## Estimated Effort

- **Phase 1 (MVP)**: 2-3 hours
- **Phase 2 (Enhancements)**: 2-3 hours
- **Documentation**: 1 hour

**Total**: ~5-7 hours

---

## References

- [Hugo Aliases Documentation](https://gohugo.io/content-management/urls/#aliases)
- [Netlify Redirects](https://docs.netlify.com/routing/redirects/)
- [Meta Refresh Best Practices](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta#attr-http-equiv)

