# RFC: Unified Autodoc Endpoint API

**Status**: Draft  
**Created**: 2025-12-31  
**Author**: AI Assistant  
**Related**: `bengal/autodoc/extractors/openapi.py`, `templates/autodoc/openapi/list.html`

---

## Summary

Autodoc's OpenAPI extractor has two output modes (`consolidate=true/false`) that produce structurally different data, forcing templates to handle both cases. This RFC proposes a unified API where endpoints are always accessible via a consistent path regardless of consolidation mode.

---

## Problem

### Current Behavior

The OpenAPI autodoc extractor populates endpoint data differently based on configuration:

| Mode | Config | Data Location | Object Type |
|------|--------|---------------|-------------|
| Consolidated | `consolidate: true` (default) | `section.metadata.endpoints` | `DocElement` |
| Individual | `consolidate: false` | `section.pages` | `Page` |

### Symptoms

1. **Template fragility**: Templates must check multiple locations:
   ```kida
   {% let endpoints = section?.metadata?.endpoints ?? section?.pages ?? [] %}
   ```

2. **Silent failures**: Templates written for one mode produce empty output in the other mode with no error.

3. **Property divergence**: `DocElement` and `Page` have different property names for similar concepts:
   - `DocElement.typed_metadata.method` vs `Page.metadata.method`
   - `DocElement.name` vs `Page.title`
   - `DocElement.description` vs `Page.metadata.summary`

4. **Link validity**: In consolidated mode, `DocElement.href` points to pages that don't exist.

### Impact

- Bug discovered: `list.html` showed "N endpoints" badge but empty table (read from wrong location)
- Template authors must understand internal autodoc architecture
- Mode switching breaks templates silently

---

## Proposed Solution

### Option A: Normalize at Template Layer (Minimal Change)

Provide a template helper that abstracts the data location:

```python
# Template function
def get_section_endpoints(section: Section) -> list[EndpointView]:
    """Return endpoints regardless of consolidation mode."""
    if endpoints := section.metadata.get("endpoints"):
        return [EndpointView.from_doc_element(ep) for ep in endpoints]
    return [EndpointView.from_page(p) for p in section.pages if is_endpoint(p)]
```

```kida
{# Template usage #}
{% let endpoints = section | get_endpoints %}
{% for ep in endpoints %}
  {{ ep.method }} {{ ep.path }} - {{ ep.summary }}
{% end %}
```

**Pros**: No autodoc changes, backward compatible  
**Cons**: Still two internal representations, helper needed everywhere

---

### Option B: Normalize at Extractor Layer (Recommended)

Always populate `section.metadata.endpoints` with a consistent structure, regardless of consolidation mode:

```python
@dataclass
class EndpointRef:
    """Unified endpoint reference for templates."""
    method: str
    path: str
    summary: str
    description: str
    deprecated: bool
    href: str | None  # None if consolidated (no individual page)
    has_page: bool    # True if individual page exists

    # Full typed metadata for detailed views
    typed_metadata: OpenAPIEndpointMetadata
```

**Extractor changes**:

```python
# In OpenAPIExtractor.build_section()
def build_section(self, tag: str, endpoints: list[DocElement]) -> Section:
    section = Section(...)

    # Always populate metadata.endpoints with EndpointRef
    section.metadata["endpoints"] = [
        EndpointRef(
            method=ep.typed_metadata.method,
            path=ep.typed_metadata.path,
            summary=ep.typed_metadata.summary,
            description=ep.description,
            deprecated=ep.typed_metadata.deprecated,
            href=ep.href if not self.config.consolidate else None,
            has_page=not self.config.consolidate,
            typed_metadata=ep.typed_metadata,
        )
        for ep in endpoints
    ]

    # Individual pages still go in section.pages when not consolidated
    if not self.config.consolidate:
        section.pages = [self.build_endpoint_page(ep) for ep in endpoints]

    return section
```

**Template usage**:

```kida
{# Always read from metadata.endpoints #}
{% for ep in section.metadata.endpoints %}
  <tr>
    <td>{{ ep.method }}</td>
    <td>
      {% if ep.has_page %}
        <a href="{{ ep.href }}">{{ ep.path }}</a>
      {% else %}
        {{ ep.path }}
      {% end %}
    </td>
    <td>{{ ep.summary }}</td>
  </tr>
{% end %}
```

**Pros**:
- Single source of truth for endpoints
- Templates don't need to know about consolidation mode
- `has_page` flag makes link rendering explicit
- Full typed metadata still available

**Cons**:
- Extractor changes required
- Slight memory increase (endpoints stored twice when not consolidated)

---

### Option C: Consolidation as Presentation Layer

Remove consolidation from the extractor entirely. Always generate individual endpoint pages, but let themes choose how to present them:

```yaml
# Theme config, not autodoc config
openapi:
  presentation:
    endpoints: inline  # Show endpoint content inline on tag page
    # OR
    endpoints: linked  # Link to individual endpoint pages
```

**Pros**: Clean separation of data generation vs. presentation  
**Cons**: Major architectural change, breaks existing configs

---

## Recommendation

**Option B** provides the best balance:

1. **Minimal breaking change**: Existing templates still work (can read `section.pages`)
2. **Clear migration path**: New templates use `section.metadata.endpoints`
3. **Explicit API**: `has_page` makes link rendering decisions obvious
4. **Full data access**: `typed_metadata` provides all endpoint details

---

## Migration Plan

### Phase 1: Add Unified API (Non-breaking)

1. Create `EndpointRef` dataclass
2. Update extractor to always populate `section.metadata.endpoints`
3. Update default templates to use new API
4. Deprecation warning if templates read `section.pages` for endpoints

### Phase 2: Documentation

1. Document `EndpointRef` in autodoc reference
2. Add template authoring guide for OpenAPI
3. Update custom theme migration guide

### Phase 3: Consider Deprecation (Future)

1. Evaluate removing `section.pages` population for endpoints
2. Or keep for backward compatibility indefinitely

---

## Implementation Details

### EndpointRef Dataclass

```python
# bengal/autodoc/types/openapi.py

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.autodoc.extractors.openapi import OpenAPIEndpointMetadata

@dataclass(frozen=True, slots=True)
class EndpointRef:
    """
    Unified endpoint reference for templates.

    Provides consistent access to endpoint data regardless of
    whether consolidate mode is enabled.
    """
    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    deprecated: bool
    tags: tuple[str, ...]

    # Linking
    href: str | None
    has_page: bool

    # Full metadata access
    typed_metadata: "OpenAPIEndpointMetadata"

    @classmethod
    def from_doc_element(
        cls,
        element: "DocElement",
        has_page: bool,
    ) -> "EndpointRef":
        """Create from DocElement (both modes)."""
        meta = element.typed_metadata
        return cls(
            method=meta.method,
            path=meta.path,
            operation_id=meta.operation_id,
            summary=meta.summary,
            description=element.description,
            deprecated=meta.deprecated,
            tags=tuple(meta.tags),
            href=element.href if has_page else None,
            has_page=has_page,
            typed_metadata=meta,
        )
```

### Template Contract

Templates can rely on:

```yaml
section.metadata.endpoints:  # Always present for tag sections
  - method: str              # HTTP method (GET, POST, etc.)
    path: str                # URL path with parameters
    summary: str             # Short description
    description: str         # Full description (may be empty)
    deprecated: bool         # Deprecation status
    href: str | None         # Link to page (None if consolidated)
    has_page: bool           # Whether individual page exists
    typed_metadata: object   # Full OpenAPIEndpointMetadata
```

---

## Alternatives Considered

### Template-only fix (current state)

```kida
{% let endpoints = section?.metadata?.endpoints ?? section?.pages ?? [] %}
```

**Rejected**: Pushes architectural complexity to template authors.

### Remove consolidation mode

**Rejected**: Valid use case for simpler API docs without per-endpoint pages.

### Virtual pages in consolidated mode

Generate Page objects that don't write files but provide consistent iteration.

**Rejected**: Overcomplicates the page lifecycle and breaks assumptions elsewhere.

---

## Open Questions

1. **Naming**: `EndpointRef` vs `EndpointView` vs `EndpointSummary`?

2. **Scope**: Should this pattern apply to other autodoc types (Python classes, CLI commands)?

3. **Anchor links**: In consolidated mode, should `href` point to `#operation-id` anchors on the tag page?

4. **Serialization**: Should `EndpointRef` be JSON-serializable for data files?

---

## Success Criteria

- [ ] Templates work identically in both consolidation modes
- [ ] No silent failures when switching modes
- [ ] Template authors don't need to understand consolidation internals
- [ ] Existing templates continue to work (backward compatible)
- [ ] Clear documentation for template authors

---

## References

- Bug: Empty endpoint table in consolidated mode (`list.html`)
- Config: `site/config/_default/autodoc.yaml` → `consolidate: true`
- Templates: `bengal/themes/default/templates/autodoc/openapi/list.html`
- Extractor: `bengal/autodoc/extractors/openapi.py`
