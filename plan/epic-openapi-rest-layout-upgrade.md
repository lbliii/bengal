# Epic: OpenAPI REST Autodoc Layout Upgrade

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-03-13 |
| **Author** | AI Assistant + Lawrence Lane |
| **Priority** | P1 (High) |
| **Depends On** | Kida 0.2.7+, `rfc-rest-api-autodoc-layouts.md` (Phase 1-4 complete) |
| **Confidence** | 85% 🟡 |

---

## Context

The REST API autodoc templates, CSS, and code generation were built in Dec 2025
(`rfc-rest-api-autodoc-layouts.md`, marked Implemented). The template layer is
~90% complete: explorer layout, sidebar nav, playground bar, param rows,
schema viewer, code samples, response tabs -- all exist.

**But the system has three critical gaps:**

1. **Endpoints don't get individual pages.** The `consolidate=True` default in
   `page_builders.py:226` skips `openapi_endpoint` elements, so `endpoint.html`
   (the flagship three-column explorer template) is never rendered. Endpoint
   cards on the home page link to dead `#anchors`.

2. **Schema pages render empty.** `schemas/User/` returns an empty
   `<div class="api-schema">` because `properties`, `enum`, and `example`
   metadata aren't reaching the template context from the extractor.

3. **Templates use Jinja2-era patterns.** All 8 partials use `{% include %}`
   with ambient `{% let %}` context. Kida 0.2.6+ added `{% def %}` + `{% slot %}`,
   `{% region %}`, `{% fragment %}`, and `{% match %}` -- none of which are used
   in the OpenAPI templates.

This epic addresses all three gaps in a phased approach.

---

## Reference: Current Page Generation

```
OpenAPI Spec
  → OpenAPIExtractor.extract()           # bengal/autodoc/extractors/openapi.py
  → DocElements: overview, endpoints[], schemas[]
  → create_openapi_sections()            # section_builders.py:255-382
  → create_pages(consolidate=True)       # page_builders.py:200-358
       ├─ openapi_overview  → SKIP (root section index handles it)
       ├─ openapi_endpoint  → SKIP (consolidate=True)  ← THE GAP
       └─ openapi_schema   → Page(template="autodoc/openapi/schema")  ✓
  → create_index_pages()                 # index_pages.py:60-100
       ├─ root section     → home.html (is_api_home)  ✓
       ├─ tag sections     → list.html (consolidated)  ✓
       └─ schemas section  → section-index.html  ✓
```

**When `consolidate=false`:**
- `openapi_endpoint` → `Page(template="autodoc/openapi/endpoint")` at
  URL `{prefix}/endpoints/{method}-{path}` (page_builders.py:438-444)
- `endpoint.html` extends `layouts/explorer.html` (three-column)
- Sidebar, code panel, playground bar all render

---

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | Every OpenAPI endpoint has its own page with three-column layout | `curl` returns 200 for each endpoint URL |
| 2 | Schema pages render properties, enums, examples | `<div class="api-schema">` is non-empty |
| 3 | Home page endpoint cards link to real pages, not `#anchors` | `grep 'href="#' home.html` returns 0 |
| 4 | Sidebar nav renders on endpoint pages with active state | Visual inspection |
| 5 | Code samples panel shows cURL/Python/JS/Go/Ruby/PHP | Visual inspection |
| 6 | Templates use `{% def %}` + `{% slot %}` for all components | No `{% include 'partials/...' %}` in endpoint/schema templates |
| 7 | Build time for demo-commerce (12 endpoints, 23 schemas) < 3s | `bengal build` timing |
| 8 | All existing tests pass | `poe test` |

---

## Phase 1: Pipeline — Enable Individual Endpoint Pages

> **Goal**: Flip `consolidate` to `false`, verify endpoint pages generate,
> fix the URL scheme, and update home page links.

### Task 1.1: Change consolidate default to `false`

**File**: `bengal/autodoc/orchestration/orchestrator.py`

The `consolidate` flag defaults to `True` at line ~259. Change the default to
`False` so each `openapi_endpoint` element becomes its own page.

**Acceptance**:
- `page_builders.py:226` no longer skips `openapi_endpoint` elements
- Build produces pages at `/api/bengal-demo-commerce/endpoints/get-users/`, etc.

**Risk**: Users who rely on consolidated mode lose it. Mitigation: keep the
config flag functional -- `consolidate: true` should still work, just not be
the default.

### Task 1.2: Improve endpoint URL scheme

**File**: `bengal/autodoc/orchestration/page_builders.py:438-444`

Current URL: `{prefix}/endpoints/{method}-{path}` (e.g., `/api/.../endpoints/get-users`)

Proposed URL: `{prefix}/{tag}/{method}-{slug}` (e.g., `/api/.../users/get-users`)

This groups endpoints by tag in the URL, matching the sidebar grouping. Falls
back to `{prefix}/endpoints/{method}-{slug}` for untagged endpoints.

**Acceptance**:
- Endpoint URLs include the tag as a path segment
- URLs are stable and deterministic (same spec → same URLs)
- `find_parent_section()` at line 396-406 correctly maps endpoints to tag sections

### Task 1.3: Fix home page endpoint card links

**File**: `bengal/themes/default/templates/autodoc/openapi/home.html:202`

Currently `ep.href` returns `#get-users` (anchor). When endpoints have pages,
the `endpoints` filter should return real page URLs. Verify the filter's
`EndpointView.href` logic handles both modes:
- `consolidate=true`: `#method-slug` anchors (current behavior)
- `consolidate=false`: `/api/.../users/get-users/` page URLs

**File**: The `endpoints` template filter that produces `EndpointView` objects.

**Acceptance**:
- `ep.href` on home page points to real endpoint pages
- `ep.has_page` returns `True` for all endpoints
- No `#anchor` links in the rendered home page

### Task 1.4: Fix tag section list.html links

**File**: `bengal/themes/default/templates/autodoc/openapi/list.html:73-79`

The template already checks `ep.has_page` and conditionally wraps in `<a>`.
Verify this works when endpoints have pages. The table rows should link to
endpoint detail pages.

**Acceptance**:
- Tag list pages (e.g., `/api/.../users/`) show endpoint table with clickable links
- Both the table view and card view link to endpoint detail pages

### Task 1.5: Verify explorer layout renders correctly

Build the demo-commerce site with `consolidate: false` and verify:
- Three-column layout (sidebar | content | code panel) renders
- Sidebar shows all endpoints grouped by tag
- Code samples panel shows generated cURL/Python/JS
- Playground bar shows method badge + path + copy button
- Parameters, request body, responses all render
- Prev/next navigation links work between endpoints

**Acceptance**: Visual review of at least 3 endpoint pages (GET, POST, DELETE).

---

## Phase 2: Pipeline — Fix Schema Page Metadata

> **Goal**: Schema detail pages render properties, enums, and examples
> instead of an empty `<div>`.

### Task 2.1: Debug schema metadata propagation

**Files**:
- `bengal/autodoc/extractors/openapi.py:327-360` (`_extract_schemas`)
- `bengal/autodoc/models/openapi.py` (`OpenAPISchemaMetadata`)
- `bengal/autodoc/orchestration/page_builders.py` (element → page metadata)
- `bengal/rendering/pipeline/autodoc_renderer.py` (template context assembly)

The schema extractor produces `DocElement` objects with `typed_metadata` containing
`OpenAPISchemaMetadata`. The `schema.html` template reads:

```kida
{% let properties = meta?.properties ?? {} %}
{% let required_props = meta?.required ?? () %}
{% let enum_vals = meta?.enum %}
{% let example_val = meta?.example %}
```

But `<div class="api-schema">` renders empty, which means either:
1. `element.typed_metadata` isn't set on the page's `autodoc_element`
2. `properties` is present but empty (schema not fully resolved)
3. `$ref` schemas aren't being dereferenced before extraction

Investigate and fix the metadata pipeline.

**Acceptance**:
- `/api/.../schemas/User/` shows the property list with names, types, required badges
- `/api/.../schemas/OrderStatus/` shows enum values
- At least one schema shows an example JSON block

### Task 2.2: Fix schema `$ref` cross-links

**Files**:
- `autodoc/openapi/partials/responses.html:113`
- `autodoc/openapi/partials/request-body.html:55`

Both templates link to `#schema-{{ schema_name | slugify }}` (page-local anchors).
These should link to the actual schema page: `/api/.../schemas/{{ schema_name }}/`.

**Acceptance**:
- "Schema: UserCreate" in request body links to `/api/.../schemas/UserCreate/`
- "Schema: User" in response links to `/api/.../schemas/User/`
- Links work from both endpoint pages and tag list pages

---

## Phase 3: Template Modernization — Kida Components

> **Goal**: Replace `{% include %}` partials with `{% def %}` + `{% slot %}`
> components. Leverage `{% region %}`, `{% match %}`, and `{% fragment %}`
> for cleaner composition and future OOB rendering.

### Task 3.1: Create `_components.html` component library

**New file**: `autodoc/openapi/_components.html`

Convert these partials from `{% include %}` files to `{% def %}` functions:

| Current Partial | New Component | Signature |
|-----------------|---------------|-----------|
| `playground-bar.html` | `playground_bar` | `(method, path, deprecated=false)` |
| `param-row.html` | `param_row` | `(param)` |
| `endpoint-header.html` | `endpoint_header` | `(element)` |
| — (new) | `param_group` | `(title, icon_name, params)` |
| — (new) | `endpoint_card` | `(ep)` |
| — (new) | `schema_card` | `(schema)` |
| — (new) | `method_badge` | `(method, size='default')` |

Use `{% slot %}` for customizable sections:

```kida
{% def section_panel(title) %}
<section class="api-endpoint__section autodoc-section">
  <h2 class="api-endpoint__section-title">{% slot header %}{{ title }}{% end %}</h2>
  {% slot %}
</section>
{% end %}
```

**Acceptance**:
- All components importable via `{% from '_components.html' import ... %}`
- Each component is self-contained (no ambient context dependencies)
- Components used from `home.html`, `endpoint.html`, `list.html`, and `schema.html`

### Task 3.2: Create `_schema.html` with `{% match %}` type dispatch

**New file**: `autodoc/openapi/_schema.html`

Replace the current `schema-viewer.html` (which uses nested `{% if %}` chains
for type dispatch) with `{% match %}`:

```kida
{% def schema_property(name, prop, required_props, depth=0) %}
  {% match prop?.type ?? 'any' %}
  {% case 'object' if depth < 4 %}
    {{ schema_viewer(prop, depth=depth + 1) }}
  {% case 'array' if prop?.items and depth < 4 %}
    {{ schema_viewer(prop.items, depth=depth + 1) }}
  {% case _ %}
    {# scalar: enum/default inline #}
  {% end %}
{% end %}

{% def schema_viewer(schema, name=none, depth=0) %}
  {% cache 'schema-' ~ (name ?? 'anon') ~ '-' ~ depth %}
  ...
  {% end %}
{% end %}
```

**Acceptance**:
- Recursive schema rendering works to depth 4
- `{% cache %}` blocks still work for performance
- Schema viewer used from `endpoint.html`, `schema.html`, `responses.html`, and `request-body.html`

### Task 3.3: Modernize `explorer.html` with `{% region %}`

**File**: `autodoc/openapi/layouts/explorer.html`

Replace the current `{% block %}` slots with `{% region %}` blocks for the
three main panels:

```kida
{% region sidebar_nav(section, current_page=page) %}
  ...
{% end %}

{% region endpoint_content() %}
  {% block content_main %}{% end %}
{% end %}

{% region code_panel() %}
  {% block code_examples %}{% end %}
{% end %}
```

This enables future `render_block('sidebar_nav', ...)` calls for OOB sidebar
updates (e.g., HTMX navigation without full page reload).

**Acceptance**:
- Full page render still works (regions behave like blocks)
- `template_metadata().regions()` returns the three region names
- Block rendering of `sidebar_nav` produces valid HTML fragment

### Task 3.4: Modernize `responses.html` with components

Replace inline `{% match %}` for status codes with a `status_badge` component.
Convert tab panels to use `{% def %}` with `{% slot %}`:

```kida
{% def response_tab(code, description) %}
  <div class="api-responses__panel" id="response-panel-{{ code }}">
    {% slot %}
  </div>
{% end %}
```

**Acceptance**:
- Response tabs render with correct status code colors
- Each response panel shows description, content type, schema ref, and example
- Tab switching JavaScript still works

### Task 3.5: Modernize `code-samples.html` with components

Convert the 6 hardcoded language panels to a loop over a `{% def %}`:

```kida
{% def code_panel(lang_id, lang_name, code) %}
<div class="api-code-samples__panel" id="code-panel-{{ lang_id }}">
  <div class="api-code-samples__code">
    <button class="api-code-samples__copy" aria-label="Copy code">
      {{ icon('copy', size=14) }}
    </button>
    <pre><code class="language-{{ lang_id }}">{{ code }}</code></pre>
  </div>
</div>
{% end %}
```

**Acceptance**:
- Same 6 languages render (cURL, Python, JS, Go, Ruby, PHP)
- Copy buttons work
- Code samples include auth headers and request body from metadata
- DRY: single `{% def %}` instead of 6 copy-pasted blocks

### Task 3.6: Update `endpoint.html` to use component imports

Replace all `{% include %}` calls with `{% from %}` imports:

```kida
{% from 'autodoc/openapi/_components.html' import playground_bar, param_group %}
{% from 'autodoc/openapi/_schema.html' import schema_viewer %}
```

**Acceptance**:
- `endpoint.html` has zero `{% include 'partials/...' %}` calls
- All data flows through explicit function arguments
- Template renders identically to the include-based version

### Task 3.7: Update `home.html` to use shared components

Replace inline endpoint card markup with `{{ endpoint_card(ep) }}` and
schema card markup with `{{ schema_card(schema) }}`.

**Acceptance**:
- Home page renders identically
- Cards use same component as `list.html`
- Endpoint cards link to real pages (not anchors)

### Task 3.8: Delete superseded partials

Once all templates use `_components.html` and `_schema.html`, remove:

```
partials/playground-bar.html    → playground_bar()
partials/param-row.html         → param_row()
partials/schema-viewer.html     → schema_viewer()
```

Keep these as partials (still included, not easily componentized):
```
partials/endpoint-header.html   (complex, uses url_for)
partials/sidebar-nav.html       (per-page, needs section context)
partials/code-samples.html      (if not fully converted)
partials/responses.html         (if not fully converted)
partials/request-body.html      (if not fully converted)
```

**Acceptance**:
- Deleted partials are not imported anywhere
- Build succeeds with no template-not-found errors
- All endpoint, schema, home, and list pages render correctly

---

## Phase 4: CSS Polish & Responsive

> **Goal**: Ensure the three-column layout looks great at all breakpoints
> and the design matches Bengal's neumorphic card style.

### Task 4.1: Audit explorer layout at breakpoints

Test `layouts/explorer.html` at:
- **> 1400px**: Three columns (sidebar 250px | content flex | code 400px)
- **1200-1400px**: Two columns (sidebar 220px | content flex), code panel hidden
- **900-1200px**: Two columns (sidebar 200px | content flex)
- **< 900px**: Single column, sidebar as mobile overlay

Fix any layout issues. The CSS grid definitions exist in `autodoc.css:1671-1717`
and responsive overrides at `autodoc.css:2789-2843`.

**Acceptance**: Layout renders correctly at all breakpoints (visual review).

### Task 4.2: Add neumorphic shadows to schema viewer

The param rows and schema viewer should use Bengal's neumorphic shadow tokens:
- `--neumorphic-enhanced-subtle` for cards
- `--neumorphic-enhanced-hover` for hover states

Currently, `.api-schema-viewer` uses flat borders but `.autodoc-member` already
uses neumorphic shadows. Align them.

**Acceptance**: Schema viewer cards match the visual weight of autodoc member cards.

### Task 4.3: Dark code panel palette audit

The right code panel uses hardcoded dark values in places:
- `autodoc.css:1204`: `background: #0b0c0e` (should be `var(--gray-950)`)
- `autodoc.css:1322`: `background: #111214` (should be `var(--gray-900)`)

Ensure all dark panel colors use Bengal's gray scale tokens so they adapt
to palette changes.

**Acceptance**: Code panel renders correctly in all 5 Bengal palettes.

### Task 4.4: Sidebar active state and scroll behavior

Verify the sidebar:
- Highlights the current endpoint with `api-sidebar-nav__endpoint--active`
- Scrolls to the active item on page load
- Collapse/expand groups work via `<details>` elements
- Search input filters endpoints (JavaScript enhancement, optional)

**Acceptance**: Sidebar active state is visually clear and scroll position is correct.

---

## Phase 5: Testing & Documentation

> **Goal**: Test coverage for the new page generation and template rendering.

### Task 5.1: Add integration test for endpoint page generation

**File**: `tests/integration/test_openapi_autodoc.py` (new or extend existing)

Test that building with the demo-commerce spec produces:
- 12 endpoint pages at expected URLs
- 23 schema pages at expected URLs
- 1 home page
- 4+ tag section pages
- Each endpoint page uses `autodoc/openapi/endpoint` template
- Each schema page uses `autodoc/openapi/schema` template

### Task 5.2: Add template rendering test for endpoint.html

Verify that `endpoint.html` renders with mock `DocElement` data:
- Playground bar with method + path
- Parameters grouped by location
- Request body with schema viewer
- Response tabs with status codes
- Code samples in all 6 languages

### Task 5.3: Add template rendering test for schema.html

Verify that `schema.html` renders non-empty content:
- Properties table with names, types, required badges
- Enum values for enum schemas
- Example JSON for schemas with examples
- "Used In" cross-references

### Task 5.4: Add performance regression test

**File**: `tests/performance/test_autodoc_render_regression.py` (extend)

Add a benchmark for `consolidate=false` mode:
- Measure build time for demo-commerce spec
- Assert < 3s for 12 endpoints + 23 schemas
- Compare with consolidated mode baseline

### Task 5.5: Update site documentation

Update the Bengal docs site to explain:
- How `consolidate: true` vs `false` works
- The URL scheme for endpoint pages
- How to customize the explorer layout
- Available template components for theme authors

---

## Task Dependency Graph

```
Phase 1 (Pipeline)           Phase 2 (Schema Fix)
├─ 1.1 consolidate=false     ├─ 2.1 debug metadata
├─ 1.2 URL scheme            └─ 2.2 fix $ref links
├─ 1.3 home page links              │
├─ 1.4 list page links              │
└─ 1.5 visual verification          │
       │                            │
       ▼                            ▼
Phase 3 (Template Modernization) ←──┘
├─ 3.1 _components.html
├─ 3.2 _schema.html ({% match %})
├─ 3.3 explorer.html ({% region %})
├─ 3.4 responses.html
├─ 3.5 code-samples.html
├─ 3.6 endpoint.html (imports)
├─ 3.7 home.html (imports)
└─ 3.8 delete old partials
       │
       ▼
Phase 4 (CSS Polish)          Phase 5 (Testing)
├─ 4.1 responsive audit      ├─ 5.1 integration test
├─ 4.2 neumorphic shadows    ├─ 5.2 endpoint render test
├─ 4.3 dark panel palette    ├─ 5.3 schema render test
└─ 4.4 sidebar behavior      ├─ 5.4 perf regression
                              └─ 5.5 docs update
```

Phase 1 and 2 are independent and can run in parallel.
Phase 3 depends on Phase 1 (endpoints must exist as pages).
Phase 3 depends on Phase 2 (schema data must reach templates).
Phase 4 and 5 depend on Phase 3 (templates must be modernized first).

---

## Estimated Effort

| Phase | Tasks | Estimate | Complexity |
|-------|-------|----------|------------|
| Phase 1: Pipeline | 5 | 2-3 hours | Medium (config + URL changes) |
| Phase 2: Schema Fix | 2 | 1-2 hours | Medium (debugging metadata) |
| Phase 3: Templates | 8 | 4-6 hours | High (component refactor) |
| Phase 4: CSS Polish | 4 | 1-2 hours | Low (audit + token fixes) |
| Phase 5: Testing | 5 | 2-3 hours | Medium (integration tests) |
| **Total** | **24** | **10-16 hours** | |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `consolidate=false` breaks existing sites | High | Low | Keep flag functional; only change default |
| Schema metadata is fundamentally missing from extractor | Medium | Medium | Phase 2 investigation may reveal deeper extractor gaps |
| Kida `{% def %}` + `{% slot %}` has edge cases in recursive templates | Medium | Low | Kida 0.2.7 fixed nested slot passthrough |
| Build performance degrades with 12+ extra pages | Low | Low | `{% cache %}` already in schema viewer; demo spec is small |
| `{% region %}` not backward-compatible with existing theme overrides | Medium | Low | Regions degrade to blocks if not called via `render_block` |

---

## Related Documents

- `plan/rfc-rest-api-autodoc-layouts.md` — Original RFC (Phase 1-4 marked Implemented)
- `plan/rfc-autodoc-unified-endpoint-api.md` — Unified endpoint view API
- `plan/rfc-autodoc-incremental-caching.md` — Incremental caching for autodoc
- Kida `site/content/docs/syntax/functions.md` — `{% def %}` + `{% slot %}` docs
- Kida `site/content/releases/0.2.7.md` — Nested slot passthrough fix
