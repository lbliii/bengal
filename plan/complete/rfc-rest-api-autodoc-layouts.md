# RFC: Best-in-Class REST API Autodoc Layouts

| Field | Value |
|-------|-------|
| **Status** | Implemented ✅ |
| **Created** | 2025-12-27 |
| **Implemented** | 2025-12-31 |
| **Author** | AI Assistant + Lawrence Lane |
| **Priority** | P1 (High) |
| **Related** | `bengal/autodoc/extractors/openapi.py`, `bengal/themes/default/templates/autodoc/openapi/` |
| **Confidence** | 98% 🟢 |

---

## Executive Summary

This RFC defines a comprehensive template architecture for REST API documentation in Bengal, drawing inspiration from industry leaders: **Stripe** (three-column layout, language tabs), **Fern** (interactive playgrounds, modern typography), **Mintlify** (dark code panels, high-density parameters), and **ReadMe** (try-it-out functionality, response previews).

**The Vision**: Generate API documentation that developers *want* to read, with instant comprehension of endpoints, copy-paste code samples, and a visual hierarchy that guides the eye.

**Policy on Legacy Assets**:
> [!IMPORTANT]
> Any existing `autodoc` REST CSS or templates currently found in the codebase (e.g., legacy `api-docs`, `api-hub` fragments, or unused `openapi/` folders) are to be **ignored and eventually removed** in favor of this new vision. This RFC represents the source of truth for all future REST API documentation layouts in Bengal.

**Design System Alignment**:
While this vision is ambitious, it **must strictly respect the Bengal default theme design system**. All styling must use Bengal's **semantic tokens** (`--color-primary`, `--space-4`, `--text-sm`, etc.) to ensure that API documentation feels like a first-class citizen of the broader site, inheriting the user's chosen color palette and typography settings.

---

## Design System & Semantic Tokens

To maintain consistency with the Bengal ecosystem, the new REST autodoc templates adhere to the following semantic token rules:

### 1. Color System
- **Surfaces**: Use `--color-bg-primary` for the main content area and `--color-bg-secondary` for sidebars or secondary panels.
- **Borders**: Use `--border-refined-subtle` or `--color-border-light` for separators.
- **Method Badges**: Map HTTP methods to existing semantic states:
  - `GET`: `--color-method-get` (info)
  - `POST`: `--color-method-post` (success)
  - `PUT/PATCH`: `--color-method-put` / `--color-method-patch` (warning)
  - `DELETE`: `--color-method-delete` (error)
- **Typography**: Use `--font-heading` for endpoint titles and `--font-mono` for paths and code snippets.

### 2. Spacing & Elevation
- **Gaps**: Use `--autodoc-gap` (defaulting to `--space-6`) and `--autodoc-section-gap` (`--space-8`).
- **Cards**: Parameter details and response objects use the `--elevation-card` token on hover.

---

## Kida "Power Features" Integration

This architecture is built specifically for the **Kida Template Engine**, utilizing its most advanced features to ensure performance, type safety, and clean code.

### 1. Pattern Matching over `if/elif`
For HTTP methods, status code classification, and parameter locations, we use Kida's native `{% match %}` for maximum readability and performance.

```jinja
{% match method %}
    {% case 'GET' %}<span class="badge--info">GET</span>
    {% case 'POST' %}<span class="badge--success">POST</span>
    {% case _ %}<span>{{ method }}</span>
{% end %}
```

### 2. Nil-Resilient Optional Blocks
Instead of complex null checks, we use `{% with ... as ... %}` (Kida's `WithConditional`) to safely render optional sections like Request Bodies or Auth notices.

```jinja
{% with element.metadata.request_body as body %}
    {% include 'partials/request-body.html' with body=body %}
{% end %}
```

### 3. Fragment Caching
To handle large specifications (500+ endpoints), we utilize Kida's built-in `{% cache %}` block for expensive recursive components like the schema viewer.

```jinja
{% cache "schema-" ~ schema.id, depends=[schema.version] %}
    {% include 'partials/schema-viewer.html' with schema=schema %}
{% end %}
```

### 4. Layout Inheritance
We use `{% extends %}` and `{% block %}` for the layouts, allowing themes to easily override specific sections without duplicating the structural CSS grid.

---

## Template Architecture

### Standardized Template Naming Convention

All autodoc types (Python, CLI, OpenAPI) follow the same template naming pattern:

| Template | Purpose | Python | CLI | OpenAPI |
|----------|---------|--------|-----|---------|
| `home.html` | Landing page | ✓ | ✓ | ✓ |
| `list.html` | List/index view | ✓ | ✓ | ✓ (consolidated endpoints) |
| `single.html` | Individual item | ✓ | ✓ | `endpoint.html`, `schema.html` |
| `section-index.html` | Generic fallback | ✓ | ✓ | ✓ |

OpenAPI uses domain-specific names for `single.html` equivalents because endpoints and schemas have distinct rendering requirements.

### File Structure

```
bengal/themes/default/templates/autodoc/openapi/
├── # Page Templates (Standard Names)
├── home.html              # API landing (servers, auth, endpoint categories)
├── list.html              # Consolidated endpoints for a tag section
├── endpoint.html          # Single endpoint detail (single.html equivalent)
├── schema.html            # Single schema detail (single.html equivalent)
├── section-index.html     # Generic fallback for sections
│
├── # Layouts (extend base.html)
├── layouts/
│   ├── explorer.html      # Three-column "Stripe-style" layout
│   └── reference.html     # Single-column layout
│
├── # Components (Partials)
└── partials/
    ├── playground-bar.html     # Method + path + copy bar
    ├── endpoint-header.html    # Title, description, and auth badges
    ├── param-row.html          # Atomic parameter unit with badges
    ├── request-body.html       # Body schema viewer
    ├── schema-viewer.html      # Recursive tree (uses {% cache %})
    ├── responses.html          # Tabbed response viewer (uses {% match %})
    ├── code-samples.html       # Language-switched sample panels
    └── sidebar-nav.html        # Smart API navigation
```

### Component Specification: Parameter Row (`param-row.html`)

```kida
{# Bengal Parameter Row - Respects Semantic Tokens & Kida Modern Syntax #}
{% let name = param?.name ?? 'unnamed' %}
{% let type = param?.schema_type ?? 'string' %}
{% let is_required = param?.required ?? false %}

<div class="api-param-row {{ 'api-param-row--required' if is_required else '' }}">
  {% spaceless %}
  <div class="api-param-meta">
    <code class="api-param-name">{{ name }}</code>
    <span class="api-param-type">{{ type }}</span>
    {% if is_required %}
      <span class="badge badge--danger-subtle badge--sm">Required</span>
    {% end %}
  </div>
  {% end %}

  {% with param?.description as desc %}
    <div class="api-param-description prose-sm">
      {{ desc | markdownify | safe }}
    </div>
  {% end %}
</div>
```

---

## Code Sample Generation

To ensure samples are "Copy-Paste Ready", Bengal includes a specialized utility module.

### Core Utility: `bengal/rendering/template_functions/openapi.py`

This module provides the `generate_code_sample` function, which maps OpenAPI metadata to executable snippets.

```python
def generate_code_sample(
    language: str,
    method: str,
    path: str,
    *,
    base_url: str = "https://api.example.com",
    request_body: dict | None = None,
    parameters: list | None = None,
    headers: dict | None = None,
    auth_scheme: str = "Bearer",
) -> str:
    """Generate a code sample for an API endpoint."""
    ...
```

**Supported Languages**:
1. `curl` (Standard)
2. `python` (Requests)
3. `javascript` (Fetch)
4. `go` (Net/HTTP)
5. `ruby` (Net/HTTP)
6. `php` (Guzzle)

**Additional Functions**:
- `highlight_path_params(path)` - Highlight `{param}` in paths
- `method_color_class(method)` - Get CSS class for HTTP method
- `status_code_class(code)` - Get CSS class for status code
- `get_response_example(responses, code)` - Extract example from OpenAPI responses

---

## Implementation Checklist

### Phase 1: Semantic Foundation & Layout ✅
- [x] Audit `semantic.css` for HTTP method colors → Added `--color-method-*` tokens
- [x] Implement `layouts/explorer.html` using Kida's `{% block %}` system
- [x] Implement `layouts/reference.html` single-column fallback
- [x] Build `partials/playground-bar.html` with `{% spaceless %}` for clean path output

### Phase 2: High-Performance Components ✅
- [x] Build recursive `schema-viewer.html` with `{% cache %}` support
- [x] Implement `responses.html` using `{% match %}` for status code color-coding
- [x] Build `param-row.html` with `{% with ... as ... %}` for nil-resilience
- [x] Build `request-body.html` partial
- [x] Build `endpoint-header.html` partial
- [x] Build `code-samples.html` with language tabs
- [x] Build `sidebar-nav.html` for API navigation

### Phase 3: Code Generation & Functions ✅
- [x] Implement `bengal/rendering/template_functions/openapi.py`
- [x] Register `generate_code_sample` and `highlight_path_params` as global template functions
- [x] Implement code generators for: curl, python, javascript, go, ruby, php
- [x] Add utility functions: `method_color_class`, `status_code_class`, `get_response_example`

### Phase 4: Page Templates ✅
- [x] Create `home.html` landing page
- [x] Create `list.html` tag group page
- [x] Create `endpoint.html` (the hero template)
- [x] Create `schema.html` standalone schema page

---

## Success Criteria

1. **Semantic Purity**: 100% of styles use `--variable` tokens from the Bengal design system. ✅
2. **Kida Mastery**: All templates leverage `{% match %}`, `{% cache %}`, and `{% with %}` where appropriate. ✅
3. **Nil Resilience**: Zero "undefined" errors during render due to Kida's `?.`, `??`, and `{% with %}` syntax. ✅
4. **Performance**: Build time for a 500-endpoint specification remains under 4 seconds due to fragment caching. 🔲 (Not benchmarked)
5. **Copy-Paste Accuracy**: Code samples are generated dynamically from endpoint metadata. ✅

---

## Future Enhancements

The following features are planned but not implemented in this RFC:

1. **Interactive Playground (JS)**: Add JavaScript for live API testing ("Try It" functionality)
2. **Schema Expansion/Collapse (JS)**: Add JavaScript for expanding/collapsing nested schema objects
3. **Language Tab Persistence**: Store user's preferred language in localStorage
4. **Response Tab Switching (JS)**: Add JavaScript for switching between response status tabs
5. **Search in Sidebar (JS)**: Add JavaScript for filtering endpoints in the sidebar

These features require JavaScript enhancements and will be tracked separately.
