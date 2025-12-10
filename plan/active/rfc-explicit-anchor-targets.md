# RFC: Explicit Anchor Targets for Cross-References

**Status**: Draft (Reviewed)  
**Created**: 2025-12-09  
**Updated**: 2025-12-10  
**Author**: AI Assistant  
**Related**: `bengal/rendering/plugins/cross_references.py`, Sphinx migration  
**Confidence**: 82% 🟡 (Moderate-High)

---

## Executive Summary

Bengal's cross-reference system (`[[path]]` wikilinks) is powerful for page-level linking but **lacks the ability to create explicit anchor targets** at arbitrary locations within content. Sphinx/RST users can create custom anchors anywhere with `.. _label:` or MyST's `(target)=` syntax—Bengal has no equivalent.

**Recommendation**: Implement **Option A (MyST-Compatible Syntax)** — add `{#custom-id}` heading attribute syntax and a `{target}` directive for inline anchors, matching MyST Markdown conventions for ecosystem compatibility.

**Impact**: 2 new features (heading attributes + target directive), ~20 hours implementation over 2 weeks, enables Sphinx user migration.

---

## Problem Statement

### Current State

Bengal indexes headings automatically during parsing:

```python
# bengal/orchestration/content.py:506-518
# Index headings from TOC (for anchor links)
if hasattr(page, "toc_items") and page.toc_items:
    for toc_item in page.toc_items:
        heading_text = toc_item.get("title", "").lower()
        anchor_id = toc_item.get("id", "")
        if heading_text and anchor_id:
            self.site.xref_index["by_heading"].setdefault(heading_text, []).append(
                (page, anchor_id)
            )
```

Anchors are **auto-generated from heading text only**. Users cannot:
1. Override auto-generated anchor IDs
2. Create anchors on non-heading content
3. Create stable anchors that survive heading text changes

### User Impact

**Sphinx/MyST users migrating to Bengal lose**:

| Feature | Sphinx/MyST Syntax | Bengal Equivalent |
|---------|-------------------|-------------------|
| Explicit heading anchor | `## Title {#my-id}` | ❌ None |
| Inline target | `(my-target)=` | ❌ None |
| Directive anchor | `:name: my-anchor` | ❌ None |
| Cross-reference | `:ref:`my-id`` | ✅ `[[#heading-text]]` |

**Example of lost functionality**:

```markdown
<!-- Sphinx/MyST - works -->
## Installation {#install}

Later, link to it: [see installation](#install)

<!-- Bengal - broken -->
## Installation

<!-- If heading changes to "Setup", all #installation links break -->
```

### Quantified Gap

- **~35 `BengalDirective` subclasses** registered in Bengal, **0** support `:name:` option for custom anchors
- Cross-reference plugin supports **4 lookup strategies** (path, slug, id, heading), but **only headings are auto-indexed from content**
- Frontmatter `id:` works for **page-level** references only, not in-page anchors
- Current xref_index has **4 keys**: `by_path`, `by_slug`, `by_id`, `by_heading`

**Evidence**: 
- `bengal/rendering/plugins/cross_references.py:21-44` shows supported syntax
- `bengal/rendering/plugins/directives/base.py:39-385` defines `BengalDirective` base class

---

## Goals & Non-Goals

### Goals

1. **G1**: Allow custom anchor IDs on headings via `{#custom-id}` syntax (MyST-compatible)
2. **G2**: Provide `{target}` directive for creating anchors at arbitrary locations
3. **G3**: Index explicit anchors in `xref_index["by_heading"]` for `[[#anchor]]` resolution
4. **G4**: Support `:name:` option on all `BengalDirective` subclasses
5. **G5**: Maintain O(1) lookup performance with pre-built index

### Non-Goals

1. **NG1**: Intersphinx cross-project linking — separate RFC scope
2. **NG2**: Auto-numbering (`:numref:`) — requires significant TOC changes
3. **NG3**: Role-based syntax (`:ref:`, `:doc:`) — `[[]]` syntax is sufficient
4. **NG4**: Backward-incompatible heading slug changes

---

## Design Options

### Option A: MyST-Compatible `{#id}` Syntax (Recommended)

Add support for heading attributes following MyST Markdown conventions.

**Syntax**:

```markdown
## Installation {#install}

### Configuration Options {#config-opts}

Some content here.

## Another Section

Link back: [[#install|Installation section]]
```

**Implementation**:

```python
# bengal/rendering/parsers/mistune.py - modify MistuneParser class

# Add class attribute (alongside existing _HEADING_PATTERN, _HTML_TAG_PATTERN)
_EXPLICIT_ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
    r'\s*\{#([a-zA-Z][a-zA-Z0-9_-]*)\}\s*$'
)

def _inject_heading_anchors(self, html: str) -> str:
    """Inject IDs into heading tags, using custom {#id} if present."""
    # Quick rejection: skip if no headings
    if not html or not ("<h2" in html or "<h3" in html or "<h4" in html):
        return html
    
    def replace_heading(match: re.Match[str]) -> str:
        tag = match.group(1)  # 'h2', 'h3', or 'h4'
        attrs = match.group(2)  # Existing attributes
        content = match.group(3)  # Heading content
        
        # Skip if already has id= attribute
        if "id=" in attrs or "id =" in attrs:
            return match.group(0)
        
        # Check for explicit {#custom-id} in content
        id_match = self._EXPLICIT_ID_PATTERN.search(content)
        if id_match:
            slug = id_match.group(1)
            # Remove {#id} from displayed content
            content = self._EXPLICIT_ID_PATTERN.sub('', content)
        else:
            # Fall back to auto-generated slug (existing behavior)
            text = self._HTML_TAG_PATTERN.sub("", content).strip()
            if not text:
                return match.group(0)
            slug = self._slugify(text)
        
        return f'<{tag} id="{slug}"{attrs}>{content}</{tag}>'
    
    try:
        return self._HEADING_PATTERN.sub(replace_heading, html)
    except Exception as e:
        logger.warning("heading_anchor_injection_error", error=str(e))
        return html  # Safe fallback
```

**Pros**:
- ✅ MyST Markdown compatible (ecosystem standard)
- ✅ Minimal implementation (regex in existing function)
- ✅ No new directives required for headings
- ✅ Stable anchors survive heading text changes

**Cons**:
- ⚠️ Only works on headings, not arbitrary content
- ⚠️ Requires updating TOC extraction to strip `{#id}` from display

---

### Option B: `{target}` Directive for Inline Anchors

Add a lightweight directive for creating anchor targets anywhere.

**Syntax**:

```markdown
:::{target} install-note
:::

:::{note}
This important note can be linked to directly.
:::

Link to it: [[#install-note|See important note]]
```

**Implementation**:

```python
# bengal/rendering/plugins/directives/target.py

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken


@dataclass
class TargetOptions(DirectiveOptions):
    """Options for target directive."""
    pass


class TargetDirective(BengalDirective):
    """
    Create an explicit anchor target at any location.
    
    Syntax:
        :::{target} my-anchor-id
        :::
    
    The target renders as an invisible anchor element that can be
    referenced via [[#my-anchor-id]] cross-reference syntax.
    
    Use cases:
        - Anchor before a note/warning that users should link to
        - Stable anchor that survives content restructuring
        - Anchor in middle of paragraph
    
    Example:
        :::{target} important-caveat
        :::
        
        :::{warning}
        This caveat is critical for production use.
        :::
        
        See [[#important-caveat|the caveat]] for details.
    """
    
    NAMES: ClassVar[list[str]] = ["target", "anchor"]
    TOKEN_TYPE: ClassVar[str] = "target"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = TargetOptions
    
    # Validation pattern for anchor IDs
    ID_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
    
    def validate_id(self, anchor_id: str) -> str | None:
        """Validate anchor ID format."""
        if not anchor_id:
            return "Target directive requires an ID"
        if not self.ID_PATTERN.match(anchor_id):
            return (
                f"Invalid anchor ID: {anchor_id!r}. "
                f"Must start with letter, contain only letters, numbers, hyphens, underscores."
            )
        return None
    
    def parse_directive(
        self,
        title: str,
        options: TargetOptions,
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build target token."""
        anchor_id = title.strip()
        
        error = self.validate_id(anchor_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "id": anchor_id},
            )
        
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={"id": anchor_id},
        )
    
    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render target as invisible anchor."""
        error = attrs.get("error")
        if error:
            return f'<span class="directive-error" title="{self.escape_html(error)}">[target error]</span>'
        
        anchor_id = attrs.get("id", "")
        # Invisible anchor element - no visual output
        return f'<span id="{self.escape_html(anchor_id)}" class="target-anchor"></span>\n'
```

**Pros**:
- ✅ Anchors anywhere in content (not just headings)
- ✅ Consistent directive syntax
- ✅ Explicit and visible in source

**Cons**:
- ⚠️ Requires indexing directive outputs (not just headings)
- ⚠️ Slightly verbose for simple cases

---

### Option C: `:name:` Option on All Directives

Add universal `:name:` support to `BengalDirective` base class.

**Syntax**:

```markdown
:::{note}
:name: important-note

This note has a custom anchor.
:::

:::{figure} /images/arch.png
:name: architecture-diagram
:alt: Architecture diagram
:::

Link: [[#important-note]] or [[#architecture-diagram]]
```

**Implementation**:

```python
# bengal/rendering/plugins/directives/base.py - modify BengalDirective

class BengalDirective(DirectivePlugin):
    # ... existing code ...
    
    def _wrap_with_anchor(self, html: str, anchor_id: str | None) -> str:
        """Wrap rendered HTML with anchor if :name: specified."""
        if not anchor_id:
            return html
        return f'<div id="{self.escape_html(anchor_id)}">\n{html}\n</div>'
    
    def render_with_name(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render directive with optional :name: anchor."""
        # Get anchor from attrs
        anchor_id = attrs.pop("name", None)
        
        # Call subclass render
        html = self.render(renderer, text, **attrs)
        
        # Wrap with anchor if specified
        return self._wrap_with_anchor(html, anchor_id)
```

**Pros**:
- ✅ Works on all ~35 existing directives automatically
- ✅ Matches Sphinx convention exactly
- ✅ No new directive syntax to learn

**Cons**:
- ⚠️ More invasive base class change
- ⚠️ Need to update `DirectiveOptions` base class and all directive registrations
- ⚠️ Potential conflicts with directive-specific `id` attrs
- ⚠️ Requires changes to directive token handling throughout render flow

---

## Recommended Approach

**Implement all three options in phases:**

### Phase 1: `{#id}` Heading Syntax (Week 1)
- Highest impact, simplest implementation
- Covers 70% of use cases (stable heading anchors)
- 8 hours effort

### Phase 2: `{target}` Directive (Week 1-2)
- Covers remaining 25% (arbitrary anchors)
- New directive, follows established patterns
- 8 hours effort

### Phase 3: `:name:` Option (Week 2, optional)
- Nice-to-have for Sphinx parity
- Can defer if Phase 1-2 cover needs
- 4 hours effort

---

## Architecture Impact

### Affected Subsystems

**Primary**: `bengal/rendering/`
- `parsers/mistune.py`: Heading attribute parsing
- `plugins/directives/target.py`: New directive (Phase 2)
- `plugins/directives/base.py`: `:name:` support (Phase 3)

**Secondary**: `bengal/orchestration/`
- `content.py`: Update `_build_xref_index()` to index explicit anchors

**CSS**: `bengal/themes/default/assets/css/`
- `.target-anchor`: Invisible anchor styling

**No changes required**:
- `bengal/core/` — No data model changes
- `bengal/cache/` — Existing caching applies
- `bengal/health/` — Existing validators apply

### xref_index Updates

**Important**: The xref_index is built during the **discovery phase** (before rendering), but `{target}` directive anchors only exist in **rendered HTML** (after parsing). This requires a **two-phase indexing approach**.

#### Phase 1: Heading Anchors (Discovery Time)

Explicit heading IDs (`{#id}`) are extracted during TOC parsing, before the full render:

```python
# bengal/orchestration/content.py - _build_xref_index()
# This runs during discovery - headings with {#id} are captured in TOC

def _build_xref_index(self) -> None:
    """Build cross-reference index."""
    
    self.site.xref_index = {
        "by_path": {},
        "by_slug": {},
        "by_id": {},
        "by_heading": {},
        "by_anchor": {},  # NEW: explicit {target} anchors (populated post-render)
    }
    
    for page in self.site.pages:
        # ... existing indexing (by_path, by_slug, by_id) ...
        
        # Index headings from TOC (includes explicit {#id} anchors)
        # TOC is extracted during parse, which processes {#id} syntax
        if hasattr(page, "toc_items") and page.toc_items:
            for toc_item in page.toc_items:
                heading_text = toc_item.get("title", "").lower()
                anchor_id = toc_item.get("id", "")
                if heading_text and anchor_id:
                    self.site.xref_index["by_heading"].setdefault(heading_text, []).append(
                        (page, anchor_id)
                    )
                    # Also index by explicit anchor ID for direct [[#id]] references
                    self.site.xref_index["by_anchor"][anchor_id.lower()] = (page, anchor_id)
```

#### Phase 2: Target Directive Anchors (Post-Render)

`{target}` directive anchors must be indexed **after rendering** completes:

```python
# bengal/orchestration/render.py - add post-render anchor indexing

TARGET_ANCHOR_PATTERN = re.compile(r'<span\s+id="([^"]+)"\s+class="target-anchor"')

def _index_explicit_anchors(self, site: Site) -> None:
    """
    Index {target} directive anchors after rendering.
    
    Called at the end of render_pages() to capture explicit anchors
    that were rendered during the build.
    """
    for page in site.pages:
        if not page.rendered_html:
            continue
            
        for match in TARGET_ANCHOR_PATTERN.finditer(page.rendered_html):
            anchor_id = match.group(1).lower()
            # Add to xref_index (by_anchor)
            site.xref_index["by_anchor"][anchor_id] = (page, match.group(1))
```

#### Cross-Reference Resolution (Updated)

The cross-reference plugin checks both heading and explicit anchor indexes:

```python
# bengal/rendering/plugins/cross_references.py

def _resolve_heading(self, anchor: str, text: str | None = None) -> str:
    """Resolve anchor reference - check explicit anchors first."""
    anchor_key = anchor.lstrip("#").lower()
    
    # Check explicit anchors first (exact match)
    explicit = self.xref_index.get("by_anchor", {}).get(anchor_key)
    if explicit:
        page, anchor_id = explicit
        link_text = text or anchor_key.replace("-", " ").title()
        url = page.url if hasattr(page, "url") else f"/{page.slug}/"
        return f'<a href="{url}#{anchor_id}">{link_text}</a>'
    
    # Fall back to heading search
    results = self.xref_index.get("by_heading", {}).get(anchor_key, [])
    # ... existing logic ...
```

---

## Migration Path

### For Sphinx Users

**Before (Sphinx/MyST)**:
```markdown
(install)=
## Installation

Later: {ref}`install`
```

**After (Bengal)**:
```markdown
## Installation {#install}

Later: [[#install|Installation]]
```

### For Existing Bengal Users

**No breaking changes**. Auto-generated heading anchors continue to work. New syntax is additive.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/rendering/test_heading_anchors.py

def test_explicit_heading_id():
    """Test {#custom-id} syntax on headings."""
    parser = MistuneParser()
    html = parser.parse("## Installation {#install}\n\nContent", {})
    assert 'id="install"' in html
    assert "{#install}" not in html  # Stripped from display

def test_explicit_id_in_toc():
    """Test explicit IDs are indexed for cross-references."""
    html, toc = parser.parse_with_toc("## Setup {#install}", {})
    # TOC should use explicit ID, not auto-slug
    assert 'href="#install"' in toc

def test_target_directive():
    """Test {target} directive creates anchor."""
    html = parser.parse(":::{target} my-anchor\n:::\n\nContent", {})
    assert 'id="my-anchor"' in html
    assert 'class="target-anchor"' in html
```

### Integration Tests

```python
# tests/integration/test_cross_references.py

def test_wikilink_to_explicit_anchor(site_factory):
    """Test [[#explicit-id]] resolves to target directive."""
    site = site_factory("test-xref")
    # ... create pages with explicit anchors ...
    site.build()
    
    page = site.get_page("docs/linking")
    assert 'href="/docs/target-page/#my-anchor"' in page.rendered_html
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Duplicate anchor IDs | Medium | Low | Warn at build time, first-wins resolution |
| TOC display pollution | Medium | Medium | Strip `{#id}` before display text extraction |
| Performance regression | Low | Low | Regex is fast, anchor index is O(1) |
| MyST incompatibility | Low | Medium | Follow MyST spec exactly |
| xref index timing | Medium | High | Two-phase indexing (discovery + post-render) |
| Broken anchor references | Medium | Medium | Health check validates `[[#anchor]]` targets exist |

---

## Incremental Build Considerations

Explicit anchors must integrate correctly with Bengal's incremental build and caching system.

### Cache Invalidation Rules

1. **Heading `{#id}` changes**: When a heading's explicit ID changes, pages that reference `[[#old-id]]` should be flagged as potentially stale
2. **`{target}` directive changes**: Adding/removing/renaming a `{target}` affects the xref index
3. **Cross-page references**: If page A references `[[page-b#anchor]]` and page B's anchor changes, page A needs rebuild

### Implementation Approach

```python
# bengal/cache/dependency_tracker.py - extend anchor tracking

class DependencyTracker:
    """Track cross-reference dependencies for incremental builds."""
    
    def track_anchor_reference(self, source_page: str, target_anchor: str) -> None:
        """Record that source_page references target_anchor."""
        # Used during incremental builds to invalidate pages
        # when their referenced anchors change
        self._anchor_refs.setdefault(target_anchor, set()).add(source_page)
    
    def get_pages_referencing_anchor(self, anchor: str) -> set[str]:
        """Get all pages that reference a specific anchor."""
        return self._anchor_refs.get(anchor, set())
```

### Performance Consideration

Anchor tracking adds minimal overhead:
- Anchor extraction: O(n) per page during render
- Index update: O(1) dictionary insertion
- Reference tracking: O(1) per cross-reference

---

## Health Check Integration

Explicit anchors require validation to catch errors at build time.

### New Health Checks

```python
# bengal/health/validators/anchors.py

class AnchorValidator:
    """Validate explicit anchors and cross-references."""
    
    def validate_duplicate_anchors(self, site: Site) -> list[HealthIssue]:
        """Check for duplicate anchor IDs within a page."""
        issues = []
        for page in site.pages:
            seen_anchors: dict[str, int] = {}
            # Scan rendered HTML for id= attributes
            for match in re.finditer(r'id="([^"]+)"', page.rendered_html or ""):
                anchor = match.group(1)
                seen_anchors[anchor] = seen_anchors.get(anchor, 0) + 1
            
            for anchor, count in seen_anchors.items():
                if count > 1:
                    issues.append(HealthIssue(
                        level="warning",
                        message=f"Duplicate anchor ID '{anchor}' ({count} occurrences)",
                        file=str(page.source_path),
                    ))
        return issues
    
    def validate_anchor_references(self, site: Site) -> list[HealthIssue]:
        """Check that all [[#anchor]] references resolve to existing anchors."""
        issues = []
        valid_anchors = set(site.xref_index.get("by_anchor", {}).keys())
        valid_anchors.update(site.xref_index.get("by_heading", {}).keys())
        
        for page in site.pages:
            # Find all [[#anchor]] references in source content
            for match in re.finditer(r'\[\[#([^\]|]+)', page.content):
                anchor = match.group(1).lower()
                if anchor not in valid_anchors:
                    issues.append(HealthIssue(
                        level="warning",
                        message=f"Broken anchor reference '[[#{match.group(1)}]]'",
                        file=str(page.source_path),
                    ))
        return issues
```

### CLI Integration

```bash
# Add to health check output
bengal health

# Example output:
# ✓ Pages: 42 valid
# ✓ Links: 156 valid
# ⚠ Anchors: 2 issues
#   - docs/guide.md: Duplicate anchor ID 'install' (2 occurrences)
#   - docs/api.md: Broken anchor reference '[[#nonexistent]]'
```

---

## Implementation Plan

### Phase 1: Heading `{#id}` Syntax (Week 1)

- [ ] Add `_EXPLICIT_ID_PATTERN` class attribute to `MistuneParser`
- [ ] Update `_inject_heading_anchors()` to extract and use `{#id}`
- [ ] Update `_extract_toc()` to strip `{#id}` from display text
- [ ] Index explicit heading IDs in `by_anchor` during `_build_xref_index()`
- [ ] Add unit tests for explicit ID parsing
- [ ] Add unit tests for TOC display text (no `{#id}` visible)
- [ ] Update documentation with `{#id}` syntax

### Phase 2: `{target}` Directive (Week 1-2)

- [ ] Create `bengal/rendering/plugins/directives/target.py`
- [ ] Register `TargetDirective` in `__init__.py`
- [ ] Add `_index_explicit_anchors()` post-render hook in `render.py`
- [ ] Add CSS for `.target-anchor` (invisible by default)
- [ ] Add unit tests for `{target}` directive
- [ ] Add integration tests for cross-page `[[#anchor]]` resolution
- [ ] Document directive syntax

### Phase 3: Health Checks & Validation (Week 2)

- [ ] Create `bengal/health/validators/anchors.py`
- [ ] Add `validate_duplicate_anchors()` check
- [ ] Add `validate_anchor_references()` check
- [ ] Integrate anchor validation into `bengal health` CLI
- [ ] Add tests for health check validators

### Phase 4: `:name:` Option (Week 2-3, optional)

- [ ] Add `name` field to `DirectiveOptions` base class
- [ ] Update `BengalDirective` render flow to wrap with anchor
- [ ] Update post-render indexing to capture `:name:` anchors
- [ ] Test on sample directives (note, figure)
- [ ] Document universal `:name:` support

---

## Success Criteria

1. **`## Heading {#custom-id}`** creates anchor with custom ID (ID not shown in TOC/display)
2. **`:::{target} my-anchor`** creates invisible anchor at location
3. **`[[#custom-id]]`** resolves to explicit anchor with O(1) lookup
4. **Existing auto-anchors** continue to work unchanged
5. **Sphinx users** can migrate with predictable syntax mapping
6. **Health checks** warn on:
   - Duplicate anchor IDs within a page
   - Broken `[[#anchor]]` references to non-existent anchors
7. **Incremental builds** correctly invalidate pages when anchor dependencies change
8. **Case-insensitive** anchor resolution (matching existing heading behavior)

---

## References

### External Documentation
- [MyST Markdown - Targets and Cross-References](https://myst-parser.readthedocs.io/en/latest/syntax/cross-referencing.html)
- [Sphinx - Cross-referencing arbitrary locations](https://www.sphinx-doc.org/en/master/usage/restructuredtext/roles.html#ref-role)

### Bengal Source Files
- `bengal/rendering/plugins/cross_references.py:21-44` — CrossReferencePlugin syntax docs
- `bengal/orchestration/content.py:506-518` — xref_index heading indexing
- `bengal/rendering/parsers/mistune.py:717-852` — `_inject_heading_anchors()` implementation
- `bengal/rendering/plugins/directives/base.py:39-385` — BengalDirective base class
- `bengal/rendering/plugins/directives/options.py` — DirectiveOptions base class

### Related Tests
- `tests/unit/rendering/test_crossref.py` — Cross-reference unit tests
- `tests/unit/rendering/test_parser_configuration.py` — Parser configuration tests

---

## Review Notes (2025-12-10)

### Verified Claims ✅
- xref_index heading indexing at `content.py:506-518` — exact code match
- CrossReferencePlugin supports 4 lookup strategies — confirmed in docstring
- Auto-generated anchors only, no custom overrides — confirmed in `_inject_heading_anchors()`
- Frontmatter `id:` works for page-level only — confirmed at `content.py:502-504`
- BengalDirective base class structure — confirmed in `base.py`

### Corrections Made
- **Directive count**: Changed from "44" to "~35" based on actual grep of `BengalDirective` subclasses
- **xref timing issue**: Added two-phase indexing approach (discovery + post-render)
- **Implementation code**: Aligned with actual class structure (class attributes, error handling)

### Added Sections
- Incremental Build Considerations
- Health Check Integration
- Phase 3 (Health Checks) in Implementation Plan

### Open Questions
1. Should explicit anchor IDs be case-sensitive or case-insensitive? (Current heading lookup uses `.lower()`)
2. Should `[[#anchor]]` resolution prefer explicit anchors over auto-generated heading anchors when both exist?
3. How should duplicate anchor warnings interact with strict mode? (Error vs. warning)

---

## Appendix: Syntax Comparison

| Feature | Sphinx RST | MyST Markdown | Bengal (Proposed) |
|---------|-----------|---------------|-------------------|
| Heading anchor | N/A (use label) | `## Title {#id}` | `## Title {#id}` ✅ |
| Inline target | `.. _label:` | `(label)=` | `:::{target} label` |
| Directive anchor | `:name: id` | `:name: id` | `:name: id` (Phase 3) |
| Reference | `:ref:`label`` | `{ref}`label`` | `[[#label]]` |
| Page reference | `:doc:`path`` | `{doc}`path`` | `[[path]]` |

