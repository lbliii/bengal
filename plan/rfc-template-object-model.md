# RFC: Template Object Model Improvements

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2024-12-30 |
| **Updated** | 2024-12-30 |
| **Author** | Bengal Team |
| **Scope** | Breaking Change (Major Version) |

## Summary

Improve the ergonomics and consistency of Bengal's template object model by:
1. Renaming `page.content` (raw markdown) to `page._source`
2. Making `page.content` return rendered HTML (matching user expectations)
3. Documenting the underscore prefix convention (`_` = internal/comparison use)

## Motivation

### The Core Problem: API Inconsistency

Bengal's Page object has a naming inconsistency that violates the principle of least surprise:

| Property | Returns | Intuition | Verdict |
|----------|---------|-----------|---------|
| `page.content` | Raw markdown | "The content to display" | ❌ Misleading |
| `page.html` | Rendered HTML | Clear, but requires discovery | ⚠️ Hidden |
| `content` (context var) | Rendered HTML | Matches expectation | ✅ Correct |

**The mismatch**: `page.content` sounds like displayable content but returns raw markdown. The actual rendered HTML is available via `page.html`, but this requires reading documentation to discover.

### Why This Matters

**1. Convention Violation**

Bengal already uses underscore prefix for internal/raw data:

```python
page._path      # Site-relative URL (internal, for comparisons)
page.href       # URL with baseurl (for template output)

page._section   # Parent section object (internal)
section         # Context wrapper (for templates)
```

`page.content` violates this convention—it's raw data without the underscore signal.

**2. Protocol Documentation Bug**

The `PageLike` protocol incorrectly documents `content`:

```python
# bengal/core/page/computed.py:98-100
@property
def content(self) -> str:
    """Rendered HTML content."""  # ❌ WRONG - actually returns raw markdown
    ...
```

This documentation bug can mislead developers building custom page types.

**3. Competitive Misalignment**

| SSG | Raw Source | Rendered Output |
|-----|------------|-----------------|
| Hugo | `.RawContent` | `.Content` |
| Jekyll | N/A | `content` |
| Eleventy | N/A | `content` |
| Zola | N/A | `page.content` |
| **Bengal (current)** | `page.content` | `content` (context var) |
| **Bengal (proposed)** | `page._source` | `page.content` |

Developers migrating from Hugo or Zola expect `page.content` to be displayable.

**4. Undiscoverability of `page.html`**

The correct property (`page.html`) exists but:
- Requires documentation lookup
- Not intuitive (sounds like file format, not content)
- Inconsistent with `page.content` naming pattern

### Current State Analysis

**Template Usage (Verified)**

Existing Bengal templates correctly use the context variable:

```kida
{# All bundled templates use this pattern #}
{{ content | safe }}
```

Evidence: `grep -r "{{ content" bengal/themes/` returns 20+ correct usages. Zero templates use `{{ page.content | safe }}`.

**Why templates work today**: The `content` context variable is set to rendered HTML by `build_page_context()`:

```python
# bengal/rendering/context/__init__.py:363
"content": Markup(content) if content else Markup(""),
```

**Risk**: New theme developers may try `page.content` before discovering the context variable pattern, especially those coming from Hugo/Zola.

## Design

### The Underscore Convention

Formalize Bengal's existing pattern:

| Prefix | Meaning | Use Case |
|--------|---------|----------|
| `_` prefix | Internal/raw data | Logic, comparisons, analysis |
| No prefix | Template-ready | Direct HTML output |

Examples already following this convention:
- `page._path` vs `page.href`
- `page._section` vs `section` (context)

### Proposed Changes

#### Page Object Properties

```python
# RENAMED: Raw source gets underscore prefix (following convention)
page._source        # Raw markdown (was: page.content)

# CHANGED: Content now means displayable content  
page.content        # Rendered HTML (was: page.html)

# KEPT: These already follow the convention
page._path          # Site-relative URL (internal)
page.href           # Full URL (template output)
page._section       # Parent section (internal)

# KEPT: Template-ready properties (unchanged)
page.title          # Display title
page.date           # Publication date
page.tags           # Tags list
page.metadata       # Raw frontmatter dict
page.toc            # Table of contents HTML
page.toc_items      # Structured TOC data
page.summary        # Auto-generated excerpt
page.plain_text     # Plain text (for search/LLM)

# DEPRECATED: Will be removed in v2.0
page.html           # Use page.content instead
```

#### Context Variables

```python
# KEPT: Pre-computed shortcuts (unchanged behavior)
content     = page.content      # Rendered HTML (now consistent!)
title       = page.title
toc         = page.toc
toc_items   = page.toc_items
```

### Migration Path

#### Phase 0: Immediate (v0.2.x patch)

Fix documentation bug in `PageLike` protocol:

```python
# Before (incorrect)
@property
def content(self) -> str:
    """Rendered HTML content."""

# After (accurate)
@property
def content(self) -> str:
    """Raw markdown source content."""
```

#### Phase 1: Add Aliases (v0.3.0)

Non-breaking: Add new names as aliases.

```python
@property
def _source(self) -> str:
    """Raw markdown source."""
    return self._raw_content

# page.content still returns raw (old behavior)
# page.html still returns rendered (unchanged)
```

#### Phase 2: Deprecation Warnings (v0.4.0)

Warn when accessing raw content via `page.content`:

```python
@property  
def content(self) -> str:
    warnings.warn(
        "page.content will return rendered HTML in v1.0. "
        "Use page._source for raw markdown.",
        DeprecationWarning,
        stacklevel=2
    )
    return self._raw_content  # Still old behavior
```

Also deprecate `page.html`:

```python
@property
def html(self) -> str:
    warnings.warn(
        "page.html is deprecated. Use page.content instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return self._rendered_html
```

#### Phase 3: Flip Default (v1.0.0)

Breaking change in major version.

```python
@property
def content(self) -> str:
    """Rendered HTML content."""
    return self._rendered_html

@property
def _source(self) -> str:
    """Raw markdown source."""
    return self._raw_content

# page.html removed (use page.content)
```

## Documentation Updates

### Update Theme Variables Reference

```markdown
## Page Properties

### Content Properties

| Property | Returns | Use For |
|----------|---------|---------|
| `page.content` | Rendered HTML | Template output |
| `page._source` | Raw markdown | Word count, analysis |
| `page.plain_text` | Plain text | Search indexing |
| `page.summary` | Excerpt | Previews, cards |

### The Underscore Convention

Properties prefixed with `_` are for internal use:
- Use in comparisons and logic
- NOT for direct template output

Properties without `_` are for templates:
- Use in HTML output
- Already include baseurl where applicable
```

### Update Quick Start Examples

```kida
{# Recommended: Use context variable #}
{{ content | safe }}

{# Also works: Access via page object #}
{{ page.content | safe }}
```

## Alternatives Considered

### Alternative A: Keep Current + Better Docs

Just improve documentation without changing names.

**Rejected because**:
- Doesn't fix the convention violation
- Protocol documentation would remain confusing
- Hugo/Zola migrants still surprised

### Alternative B: `page.source` (no underscore)

Use `page.source` instead of `page._source`.

**Rejected because**:
- Doesn't follow the established underscore convention for internal/raw properties
- `source` without underscore suggests it's template-ready

### Alternative C: `page.raw`

Use `page.raw` for raw content.

**Rejected because**:
- `raw` is ambiguous (raw what?)
- `_source` is clearer and matches common terminology

### Alternative D: `page.markdown`

Use `page.markdown` for raw content.

**Rejected because**:
- Bengal supports multiple source formats (not just markdown)
- Would be misleading for RST or HTML source files

## Impact

### Breaking Changes (v1.0)

- `page.content` returns rendered HTML instead of raw markdown
- `page.html` removed (replaced by `page.content`)
- Code using `page.content` for word count/analysis must change to `page._source`

### Affected Code Patterns

**Internal Bengal code** (must update):

```python
# Before:
word_count = len(page.content.split())
content_hash = hash(page.content)

# After:
word_count = len(page._source.split())
content_hash = hash(page._source)
```

**Templates** (no change needed):

```kida
{# Already correct - uses context variable #}
{{ content | safe }}

{# Will work after v1.0 - page.content returns HTML #}
{{ page.content | safe }}
```

### Theme Compatibility Matrix

| Pattern | v0.3 | v0.4 | v1.0 |
|---------|------|------|------|
| `{{ content \| safe }}` | ✅ Works | ✅ Works | ✅ Works |
| `{{ page.content \| safe }}` | ❌ Raw MD | ⚠️ Warning + Raw MD | ✅ Works |
| `{{ page.html \| safe }}` | ✅ Works | ⚠️ Warning | ❌ Removed |
| `{{ page._source }}` | ✅ Raw MD | ✅ Raw MD | ✅ Raw MD |

## Success Criteria

### Measurable Goals

1. **Protocol accuracy**: `PageLike.content` docstring matches actual behavior
2. **Convention compliance**: All raw data properties use underscore prefix
3. **Migration success**: < 5 support requests during deprecation period
4. **Theme compatibility**: All bundled themes pass tests through v1.0

### Validation Steps

- [ ] `grep -r "page\.content" bengal/` shows no direct template usage
- [ ] All internal code using `page.content` for raw access migrated to `page._source`
- [ ] Deprecation warnings appear in test suite (none silenced)
- [ ] Theme scaffolding generates correct patterns

## Timeline

| Phase | Version | Changes | Target Date |
|-------|---------|---------|-------------|
| 0 | v0.2.x | Fix PageLike protocol docstring | Immediate |
| 1 | v0.3.0 | Add `page._source` alias | Q1 2025 |
| 2 | v0.4.0 | Deprecation warnings | Q2 2025 |
| 3 | v1.0.0 | `page.content` returns rendered HTML | Q4 2025 |

## Open Questions

1. **Should `page.html` be kept as deprecated alias through v1.x?**
   - Pro: Smoother migration for external themes
   - Con: Confusing to have two ways to get same data

2. **Should we add `page.rendered` as an alias during Phase 1?**
   - Pro: More explicit than `content`
   - Con: More API surface to maintain

## References

- Hugo Page Variables: https://gohugo.io/variables/page/
- Jekyll Variables: https://jekyllrb.com/docs/variables/
- Bengal `PageLike` Protocol: `bengal/core/page/computed.py:68-126`
- Bengal Context Builder: `bengal/rendering/context/__init__.py:292-400`

## Appendix: Evidence

### Codebase Analysis (2024-12-30)

```bash
# Template usage patterns
$ grep -rn "{{ content" bengal/themes/ --include="*.html" | wc -l
20  # All use context variable (correct)

$ grep -rn "{{ page.content" bengal/themes/ --include="*.html" | wc -l
0   # None use page.content directly

# Underscore convention evidence
$ grep -n "_path" bengal/core/page/metadata.py
263:    def _path(self) -> str:

$ grep -n "def href" bengal/core/page/
# Multiple files - consistent pattern
```

### Current Field Definition

```python
# bengal/core/page/__init__.py:129
content: Raw content (Markdown, etc.)

# bengal/core/page/__init__.py:159  
content: str = ""
```
