# RFC: Unified OpenAPI Template Filters

**Status**: Implemented  
**Created**: 2025-12-31  
**Implemented**: 2025-12-31  
**Author**: AI Assistant  
**Related Files**:
- `bengal/rendering/template_functions/openapi.py` (primary change location)
- `bengal/themes/default/templates/autodoc/openapi/*.html` (template consumers)

---

## Summary

Autodoc's OpenAPI system produces structurally different data based on configuration, forcing templates to handle multiple object types with 14+ lines of defensive boilerplate. This RFC proposes `endpoints` and `schemas` filters that normalize data at the template layer, providing a clean, consistent API for theme authors.

---

## Problem

### Current Template Pain

Templates require extensive defensive chaining to handle DocElement vs Page objects:

**Endpoint iteration (7 lines, repeated twice in `list.html`):**
```kida
{% let ep_typed = ep?.typed_metadata ?? {} %}
{% let ep_meta = ep?.metadata ?? {} %}
{% let ep_method = ep_typed?.method ?? ep_meta?.method ?? 'GET' %}
{% let ep_path = ep_typed?.path ?? ep_meta?.path ?? ep?.name ?? '' %}
{% let ep_summary = ep_typed?.summary ?? ep_meta?.summary ?? ep?.description ?? '' %}
{% let is_deprecated = ep_typed?.deprecated ?? ep_meta?.deprecated ?? false %}
{% let ep_href = ep?.href ?? '#' %}
```

**Endpoint iteration in `home.html` (6 lines):**
```kida
{% let ep_meta = endpoint?.typed_metadata ?? endpoint?.metadata ?? {} %}
{% let ep_method = ep_meta?.method ?? 'GET' %}
{% let ep_path = ep_meta?.path ?? endpoint?.name ?? '' %}
{% let ep_summary = ep_meta?.summary ?? '' %}
{% let is_deprecated = ep_meta?.deprecated ?? false %}
```

**Total: 20+ lines of boilerplate** across OpenAPI templates.

### Root Causes

1. **Endpoint duality**: Consolidated mode stores DocElements in `section.metadata.endpoints`, individual mode stores Pages in `section.pages`
2. **Property path differences**: `DocElement.typed_metadata.method` vs `Page.metadata.method`
3. **Broken hrefs**: In consolidated mode, `DocElement.href` points to non-existent pages
4. **No normalization layer**: Templates must understand autodoc internals

### Impact

- **14 lines of boilerplate** in `list.html` alone
- **Silent failures** when switching consolidation modes
- **Themer friction**: Must understand autodoc architecture
- **Bug discovered**: Empty endpoint table with correct count badge

---

## Proposed Solution: Template Filters

Add two filters that normalize OpenAPI data for templates:

| Filter | Input | Output | Purpose |
|--------|-------|--------|---------|
| `endpoints` | Section | `list[EndpointView]` | Normalize endpoint access |
| `schemas` | Section | `list[SchemaView]` | Normalize schema access |

### Template Before/After

**Before (endpoints):**
```kida
{% let endpoints = section?.metadata?.endpoints ?? section?.pages ?? [] %}
{% let is_consolidated = section?.metadata?.endpoints | length > 0 %}

{% for ep in endpoints %}
  {% let ep_typed = ep?.typed_metadata ?? {} %}
  {% let ep_meta = ep?.metadata ?? {} %}
  {% let ep_method = ep_typed?.method ?? ep_meta?.method ?? 'GET' %}
  {% let ep_path = ep_typed?.path ?? ep_meta?.path ?? ep?.name ?? '' %}
  {% let ep_summary = ep_typed?.summary ?? ep_meta?.summary ?? ep?.description ?? '' %}
  {% let ep_href = ep?.href ?? '#' %}

  <tr>
    <td>{{ ep_method }}</td>
    <td>
      {% if is_consolidated %}
        {{ ep_path }}
      {% else %}
        <a href="{{ ep_href }}">{{ ep_path }}</a>
      {% end %}
    </td>
  </tr>
{% end %}
```

**After (endpoints):**
```kida
{% for ep in section | endpoints %}
  <tr>
    <td>{{ ep.method }}</td>
    <td><a href="{{ ep.href }}">{{ ep.path | highlight_path_params | safe }}</a></td>
    <td>{{ ep.summary | truncate(100) }}</td>
  </tr>
{% end %}
```

**Before (schemas):**
```kida
{% let all_schemas = sec_meta?.schemas ?? () %}
{% for schema in all_schemas %}
  {% let schema_meta = schema?.typed_metadata ?? {} %}
  {% let schema_name = schema?.name ?? 'Unknown' %}
  {% let schema_type = schema_meta?.schema_type ?? 'object' %}

  <a href="{{ schema?.href ?? '#' }}">{{ schema_name }}</a>
{% end %}
```

**After (schemas):**
```kida
{% for schema in section | schemas %}
  <a href="{{ schema.href }}">{{ schema.name }}</a>
  <span class="badge">{{ schema.schema_type }}</span>
{% end %}
```

**Reduction**: 20+ lines → 0 lines of boilerplate.

---

## Implementation

### EndpointView Dataclass

```python
# bengal/rendering/template_functions/openapi.py

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement
    from bengal.core.page import Page
    from bengal.core.section import Section


@dataclass(frozen=True, slots=True)
class EndpointView:
    """
    Normalized endpoint view for templates.

    Provides consistent access to endpoint data regardless of
    whether the source is a DocElement (consolidated mode) or
    Page (individual mode).

    Attributes:
        method: HTTP method (GET, POST, etc.)
        path: URL path with parameters (/users/{id})
        summary: Short description
        description: Full description
        deprecated: Whether endpoint is deprecated
        href: Always valid - anchor in consolidated mode, page URL otherwise
        has_page: Whether an individual page exists
        operation_id: OpenAPI operationId (for advanced use)
        tags: Endpoint tags
        typed_metadata: Full OpenAPIEndpointMetadata (for advanced use)
    """
    method: str
    path: str
    summary: str
    description: str
    deprecated: bool
    href: str           # Always valid - never None
    has_page: bool
    operation_id: str | None
    tags: tuple[str, ...]
    typed_metadata: Any  # OpenAPIEndpointMetadata or None

    @classmethod
    def from_doc_element(cls, el: "DocElement", consolidated: bool) -> "EndpointView":
        """Create from DocElement (consolidated or individual mode)."""
        meta = el.typed_metadata

        # Generate anchor ID from operationId or path
        anchor_id = meta.operation_id or f"{meta.method.lower()}-{meta.path.strip('/').replace('/', '-').replace('{', '').replace('}', '')}"

        # Smart href: anchor if consolidated, page URL otherwise
        if consolidated:
            href = f"#{anchor_id}"
        else:
            href = el.href or "#"

        return cls(
            method=meta.method,
            path=meta.path,
            summary=meta.summary or "",
            description=el.description,
            deprecated=meta.deprecated,
            href=href,
            has_page=not consolidated,
            operation_id=meta.operation_id,
            tags=meta.tags or (),
            typed_metadata=meta,
        )

    @classmethod
    def from_page(cls, page: "Page") -> "EndpointView":
        """Create from Page (individual mode)."""
        meta = page.metadata
        return cls(
            method=meta.get("method", "GET"),
            path=meta.get("path", ""),
            summary=meta.get("summary", ""),
            description=meta.get("description", ""),
            deprecated=meta.get("deprecated", False),
            href=page.href or "#",
            has_page=True,
            operation_id=meta.get("operation_id"),
            tags=tuple(meta.get("tags", ())),
            typed_metadata=None,
        )
```

### SchemaView Dataclass

```python
@dataclass(frozen=True, slots=True)
class SchemaView:
    """
    Normalized schema view for templates.

    Provides consistent access to schema data for listing and linking.

    Attributes:
        name: Schema name (e.g., "User", "OrderRequest")
        schema_type: Type (object, array, string, etc.)
        description: Schema description
        href: Link to schema page (or anchor if inline)
        has_page: Whether individual page exists
        properties: Property definitions (for quick access)
        required: Required property names
        enum: Enum values (if applicable)
        example: Example value (if provided)
        typed_metadata: Full OpenAPISchemaMetadata
    """
    name: str
    schema_type: str
    description: str
    href: str
    has_page: bool
    properties: dict
    required: tuple[str, ...]
    enum: tuple | None
    example: Any
    typed_metadata: Any

    @classmethod
    def from_doc_element(cls, el: "DocElement", consolidated: bool = False) -> "SchemaView":
        """Create from DocElement."""
        meta = el.typed_metadata

        # Smart href: anchor if no page, page URL otherwise
        if consolidated or not el.href:
            href = f"#schema-{el.name}"
            has_page = False
        else:
            href = el.href
            has_page = True

        return cls(
            name=el.name,
            schema_type=meta.schema_type or "object",
            description=el.description,
            href=href,
            has_page=has_page,
            properties=dict(meta.properties) if meta.properties else {},
            required=meta.required or (),
            enum=meta.enum,
            example=meta.example,
            typed_metadata=meta,
        )
```

### Filter Functions

```python
def endpoints_filter(section: "Section") -> list[EndpointView]:
    """
    Normalize section endpoints for templates.

    Detects consolidation mode automatically and returns a list of
    EndpointView objects with consistent properties.

    Usage:
        {% for ep in section | endpoints %}
          <a href="{{ ep.href }}">{{ ep.method }} {{ ep.path }}</a>
        {% end %}

    Args:
        section: Section containing endpoints

    Returns:
        List of EndpointView objects
    """
    if section is None:
        return []

    # Detect mode from data structure
    raw_endpoints = section.metadata.get("endpoints", [])

    if raw_endpoints:
        # Consolidated mode - DocElements stored in metadata.endpoints
        return [
            EndpointView.from_doc_element(el, consolidated=True)
            for el in raw_endpoints
            if hasattr(el, 'typed_metadata') and el.typed_metadata is not None
        ]

    # Individual mode - Pages in section.pages
    pages = getattr(section, 'pages', None) or []
    return [
        EndpointView.from_page(p)
        for p in pages
        if hasattr(p, 'metadata') and (
            p.metadata.get("type") == "openapi_endpoint" or
            "method" in p.metadata
        )
    ]


def schemas_filter(section: "Section") -> list[SchemaView]:
    """
    Normalize section schemas for templates.

    Returns a list of SchemaView objects with consistent properties.

    Usage:
        {% for schema in section | schemas %}
          <a href="{{ schema.href }}">{{ schema.name }}</a>
          <span>{{ schema.schema_type }}</span>
        {% end %}

    Args:
        section: Section containing schemas (usually root API section)

    Returns:
        List of SchemaView objects
    """
    if section is None:
        return []

    raw_schemas = section.metadata.get("schemas", [])

    return [
        SchemaView.from_doc_element(el, consolidated=False)
        for el in raw_schemas
        if hasattr(el, 'typed_metadata') and el.typed_metadata is not None
    ]
```

### Registration

```python
def register(env: TemplateEnvironment, site: Site) -> None:
    """Register OpenAPI functions with template environment."""
    env.globals.update({
        "generate_code_sample": generate_code_sample,
        "highlight_path_params": highlight_path_params,
        "method_color_class": method_color_class,
        "status_code_class": status_code_class,
        "get_response_example": get_response_example,
    })
    env.filters.update({
        "highlight_path_params": highlight_path_params,
        "method_color_class": method_color_class,
        "status_code_class": status_code_class,
        "endpoints": endpoints_filter,   # NEW
        "schemas": schemas_filter,        # NEW
    })
```

---

## Template Contract

### EndpointView Properties

```yaml
section | endpoints:  # Returns list[EndpointView]
  - method: str       # HTTP method (GET, POST, etc.) - always present
    path: str         # URL path (/users/{id}) - always present
    summary: str      # Short description - may be empty
    description: str  # Full description - may be empty
    deprecated: bool  # Deprecation status - always present
    href: str         # Always valid: "#anchor" or "/page/url/"
    has_page: bool    # Whether individual page exists
    operation_id: str | None  # OpenAPI operationId
    tags: tuple[str, ...]     # Endpoint tags
    typed_metadata: object | None  # Full metadata for advanced use
```

### SchemaView Properties

```yaml
section | schemas:   # Returns list[SchemaView]
  - name: str        # Schema name (e.g., "User") - always present
    schema_type: str # Type (object, array, etc.) - always present
    description: str # Schema description - may be empty
    href: str        # Link to schema page or anchor
    has_page: bool   # Whether individual page exists
    properties: dict # Property definitions
    required: tuple[str, ...]  # Required property names
    enum: tuple | None         # Enum values if applicable
    example: Any     # Example value if provided
    typed_metadata: object | None  # Full metadata for advanced use
```

**Key guarantees:**
- `href` is **always valid** (never None, never broken)
- Properties are **directly accessible** (no chaining required)
- Works **identically** in both consolidation modes
- Consistent API between `endpoints` and `schemas`

---

## Updated Templates

### list.html (endpoints)

```kida
{#
Bengal OpenAPI List Page - Endpoint list for a tag section
#}
{% extends 'autodoc/openapi/layouts/reference.html' %}

{% let tag_name = element?.name ?? section?.title ?? page?.title ?? 'Endpoints' %}
{% let tag_desc = element?.description ?? section?.metadata?.description ?? '' %}
{% let eps = section | endpoints %}

{% block header %}
<h1 class="api-list__title">{{ tag_name }}</h1>

{% if tag_desc %}
<div class="api-list__description prose">
  {{ tag_desc | markdownify | safe }}
</div>
{% end %}

<div class="api-list__stats">
  <span class="badge badge--outline">{{ eps | length }} endpoints</span>
</div>
{% end %}

{% block content_main %}
<div class="api-list" data-autodoc="openapi" data-element="list">

  {% if eps | length > 0 %}
  <section class="api-list__endpoints autodoc-section">
    <table class="autodoc-table" data-table="endpoints">
      <thead>
        <tr>
          <th>Method</th>
          <th>Endpoint</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {% for ep in eps %}
        <tr class="{% if ep.deprecated %}api-list__row--deprecated{% end %}">
          <td class="autodoc-cell-name" data-label="Method">
            <span class="api-method api-method--sm api-method--{{ ep.method | lower }}">{{ ep.method }}</span>
          </td>
          <td class="autodoc-cell-name" data-label="Endpoint">
            <a href="{{ ep.href }}">
              <code>{{ ep.path | highlight_path_params | safe }}</code>
            </a>
            {% if ep.deprecated %}
            <span class="autodoc-badge" data-badge="deprecated">Deprecated</span>
            {% end %}
          </td>
          <td class="autodoc-cell-desc" data-label="Description">
            {{ ep.summary | truncate(100) }}
          </td>
        </tr>
        {% end %}
      </tbody>
    </table>
  </section>
  {% else %}
  <div class="autodoc-empty-state">
    {{ icon('inbox', size=48, class='autodoc-empty-state-icon') }}
    <p class="autodoc-empty-state-text">No endpoints in this category</p>
  </div>
  {% end %}

  {# Cards View #}
  {% if eps | length > 0 %}
  <section class="api-list__cards autodoc-section">
    <h2 class="autodoc-section-title">Quick Reference</h2>
    <div class="autodoc-cards">
      {% for ep in eps %}
      <a href="{{ ep.href }}" class="autodoc-card{% if ep.deprecated %} autodoc-card--deprecated{% end %}">
        <div class="autodoc-card-header">
          <span class="api-method api-method--sm api-method--{{ ep.method | lower }}">{{ ep.method }}</span>
          <code class="autodoc-card-name">{{ ep.path | highlight_path_params | safe }}</code>
        </div>
        {% if ep.summary %}
        <p class="autodoc-card-desc">{{ ep.summary | truncate(80) }}</p>
        {% end %}
        {% if ep.deprecated %}
        <span class="autodoc-badge" data-badge="deprecated">Deprecated</span>
        {% end %}
      </a>
      {% end %}
    </div>
  </section>
  {% end %}
</div>
{% end %}
```

### home.html (endpoints + schemas)

```kida
{#
Bengal OpenAPI Home Page - API landing page
#}
{% extends 'autodoc/openapi/layouts/reference.html' %}

{% let sec_meta = section?.metadata ?? {} %}
{% let api_title = section?.title ?? 'API Reference' %}
{% let api_version = sec_meta?.version ?? '1.0.0' %}
{% let description = sec_meta?.description ?? '' %}

{# Use filters for normalized access #}
{% let eps = section | endpoints %}
{% let schs = section | schemas %}

{% block header %}
<h1 class="api-home__title">{{ api_title }}</h1>
<span class="badge badge--outline">v{{ api_version }}</span>

{% if description %}
<div class="api-home__description prose">
  {{ description | markdownify | safe }}
</div>
{% end %}
{% end %}

{% block content_main %}
<div class="api-home" data-autodoc="openapi" data-element="home">

  {# Quick Stats #}
  <div class="api-home__stats">
    <div class="api-home__stat">
      <span class="api-home__stat-value">{{ eps | length }}</span>
      <span class="api-home__stat-label">Endpoints</span>
    </div>
    <div class="api-home__stat">
      <span class="api-home__stat-value">{{ schs | length }}</span>
      <span class="api-home__stat-label">Schemas</span>
    </div>
  </div>

  {# Endpoints (when no tag structure) #}
  {% if eps | length > 0 %}
  <section class="api-home__endpoints autodoc-section">
    <h2>{{ icon('list', size=18) }} Endpoints</h2>
    <div class="autodoc-cards">
      {% for ep in eps %}
      <a href="{{ ep.href }}" class="autodoc-card{% if ep.deprecated %} autodoc-card--deprecated{% end %}">
        <div class="autodoc-card-header">
          <span class="api-method api-method--sm api-method--{{ ep.method | lower }}">{{ ep.method }}</span>
          <code class="autodoc-card-name">{{ ep.path }}</code>
        </div>
        {% if ep.summary %}
        <p class="autodoc-card-desc">{{ ep.summary | truncate(80) }}</p>
        {% end %}
      </a>
      {% end %}
    </div>
  </section>
  {% end %}

  {# Schemas #}
  {% if schs | length > 0 %}
  <section class="api-home__schemas autodoc-section">
    <h2>{{ icon('database', size=18) }} Schemas</h2>
    <div class="autodoc-cards">
      {% for schema in schs %}
      <a href="{{ schema.href }}" class="autodoc-card">
        <div class="autodoc-card-header">
          <code class="autodoc-card-name">{{ schema.name }}</code>
          <span class="badge badge--outline badge--sm">{{ schema.schema_type }}</span>
        </div>
        {% if schema.description %}
        <p class="autodoc-card-desc">{{ schema.description | truncate(80) }}</p>
        {% end %}
      </a>
      {% end %}
    </div>
  </section>
  {% end %}
</div>
{% end %}
```

---

## Migration Plan

### Phase 1: Add Filters (Non-breaking)

1. Add `EndpointView` and `SchemaView` dataclasses to `template_functions/openapi.py`
2. Add `endpoints_filter` and `schemas_filter` functions
3. Register filters in `register()` function
4. Add comprehensive tests

### Phase 2: Update Default Templates

1. Update `list.html` to use `| endpoints` filter
2. Update `home.html` to use `| endpoints` and `| schemas` filters
3. Update any other templates with endpoint/schema iteration
4. Remove boilerplate code

### Phase 3: Documentation

1. Document filters in template authoring guide
2. Add before/after examples
3. Note backward compatibility (raw access still works)

---

## Comparison

| Aspect | Current | With Filters |
|--------|---------|--------------|
| Endpoint boilerplate | 14+ lines | 0 lines |
| Schema boilerplate | 5+ lines | 0 lines |
| Files changed | 0 | 1 |
| Template syntax | Complex chaining | `section \| endpoints` |
| href validity | Broken in consolidated | Always valid |
| Learning curve | High (internals) | Low (just filters) |
| Consistency | Different patterns | Same pattern for both |

---

## Success Criteria

- [x] Templates work identically in both consolidation modes
- [x] No boilerplate required for endpoint/schema access
- [x] `href` always valid (anchor or page URL)
- [x] Existing templates continue to work (backward compatible)
- [x] Filters follow established patterns (`| truncate`, `| markdownify`)
- [x] Consistent API between `endpoints` and `schemas`
- [ ] Clear documentation for themers

---

## Test Plan

```python
# tests/unit/rendering/template_functions/test_openapi_filters.py

class TestEndpointsFilter:
    def test_consolidated_mode(self):
        """Filter returns EndpointView from DocElements in consolidated mode."""
        section = create_section_with_doc_elements()

        endpoints = endpoints_filter(section)

        assert len(endpoints) == 3
        assert endpoints[0].method == "GET"
        assert endpoints[0].href.startswith("#")  # Anchor link
        assert endpoints[0].has_page is False

    def test_individual_mode(self):
        """Filter returns EndpointView from Pages in individual mode."""
        section = create_section_with_pages()

        endpoints = endpoints_filter(section)

        assert len(endpoints) == 3
        assert endpoints[0].method == "GET"
        assert endpoints[0].href.startswith("/")  # Page URL
        assert endpoints[0].has_page is True

    def test_empty_section(self):
        """Filter handles empty sections gracefully."""
        assert endpoints_filter(create_empty_section()) == []

    def test_none_section(self):
        """Filter handles None gracefully."""
        assert endpoints_filter(None) == []


class TestSchemasFilter:
    def test_returns_schema_views(self):
        """Filter returns SchemaView from DocElements."""
        section = create_section_with_schemas()

        schemas = schemas_filter(section)

        assert len(schemas) == 2
        assert schemas[0].name == "User"
        assert schemas[0].schema_type == "object"
        assert schemas[0].href is not None

    def test_schema_properties_accessible(self):
        """SchemaView provides direct property access."""
        section = create_section_with_schemas()
        schema = schemas_filter(section)[0]

        assert isinstance(schema.properties, dict)
        assert isinstance(schema.required, tuple)

    def test_empty_section(self):
        """Filter handles sections without schemas."""
        assert schemas_filter(create_empty_section()) == []


class TestTemplateIntegration:
    def test_endpoints_filter_in_template(self):
        """Filter works correctly in actual template."""
        template = env.from_string("""
        {% for ep in section | endpoints %}
        {{ ep.method }} {{ ep.path }} -> {{ ep.href }}
        {% end %}
        """)

        result = template.render(section=section)

        assert "GET /users" in result
        assert "#" in result or "/" in result

    def test_schemas_filter_in_template(self):
        """Filter works correctly in actual template."""
        template = env.from_string("""
        {% for s in section | schemas %}
        {{ s.name }}: {{ s.schema_type }}
        {% end %}
        """)

        result = template.render(section=section)

        assert "User: object" in result
```

---

## References

- **Templates**: `themes/default/templates/autodoc/openapi/*.html`
- **Filter location**: `rendering/template_functions/openapi.py`
- **Consolidate config**: `orchestrator.py:584`
- **Section metadata**: `section_builders.py:293-294`
