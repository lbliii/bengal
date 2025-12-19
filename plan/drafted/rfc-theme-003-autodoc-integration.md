# RFC-003: Autodoc Theme Integration

**Status**: Draft  
**Created**: 2024-12-08  
**Part of**: [Theme Architecture Series](rfc-theme-architecture-series.md)  
**Priority**: P2 (Medium)  
**Dependencies**: RFC-001 (Theme Configuration)  
**Note**: Renumbered from RFC-007 in series refactor; template dependencies dropped  

---

## Summary

Move autodoc HTML templates from `bengal/autodoc/` into the theme system (`themes/default/templates/`), making autodoc output a first-class citizen of Bengal's theming architecture. Autodoc module retains extraction logic, models, and orchestration while delegating presentation entirely to themes.

---

## Problem Statement

### Current State

Autodoc currently maintains its own template system parallel to Bengal's theme architecture:

```
bengal/autodoc/
├── templates/              # Markdown + Jinja2 templates (legacy)
│   ├── base/
│   ├── python/
│   ├── cli/
│   ├── openapi/
│   └── macros/
├── html_templates/         # New HTML templates (in progress)
│   ├── module.html
│   └── section-index.html
└── virtual_orchestrator.py # Already looks for theme templates
```

### Problems

1. **Duplication**: Two template systems with similar patterns (base → extends → partials)
2. **Inconsistent UX**: Autodoc pages may not match site theme (different nav, footer, typography)
3. **User customization friction**: Users can't override autodoc templates via normal theme mechanisms
4. **Maintenance burden**: Changes to base patterns must be applied in two places
5. **No shared assets**: Can't easily reuse theme CSS classes, JS behaviors, icons, macros

### Evidence

The virtual orchestrator already anticipates theme integration:

```python
# bengal/autodoc/virtual_orchestrator.py:92-95
if self.site.theme:
    theme_templates = self._get_theme_templates_dir()
    if theme_templates:
        template_dirs.append(str(theme_templates))
```

Virtual pages already specify theme template names:

```python
# bengal/autodoc/virtual_orchestrator.py:405
template_name="autodoc/python/module",
```

The theme already has an `autodoc/python/` section:

```
themes/default/templates/autodoc/python/
├── home.html    # Extends base.html
├── list.html    # Extends base.html
└── single.html  # Extends base.html - uses {{ content | safe }}
```

---

## Proposal

### Design Principle

**Autodoc = Extraction + Orchestration. Theme = Presentation.**

Autodoc extracts documentation from source code, creates DocElement models, and generates virtual pages. The theme is responsible for rendering those pages using templates that integrate with the site's overall design.

### What Stays in `bengal/autodoc/`

| Component | Purpose | Files |
|-----------|---------|-------|
| **Extractors** | Parse source code into DocElements | `extractors/python.py`, `extractors/cli.py`, `extractors/openapi.py` |
| **Models** | DocElement, metadata structures | `base.py`, `models.py` |
| **Orchestrators** | Generate virtual pages/sections | `virtual_orchestrator.py`, `cli_orchestrator.py` |
| **Generators** | Write markdown files (legacy mode) | `generators/` |
| **Fallback Templates** | Minimal HTML when theme lacks templates | `fallback/` (new, minimal) |

### What Moves to `themes/default/templates/`

```
themes/default/templates/
├── autodoc/python/                  # API documentation pages
│   ├── home.html                   # API root index (existing)
│   ├── list.html                   # Section listing (existing)
│   ├── single.html                 # Single page wrapper (existing)
│   ├── module.html                 # Python module content ← NEW
│   ├── class.html                  # Python class content ← NEW
│   ├── function.html               # Python function content ← NEW
│   └── partials/                   # API-specific partials ← NEW
│       ├── class-card.html         # Class as collapsible card
│       ├── function-card.html      # Function as collapsible card
│       ├── method-item.html        # Method within class
│       ├── attributes-table.html   # Attributes table
│       ├── parameters-table.html   # Parameters table
│       ├── signature.html          # Code signature block
│       └── badges.html             # Type/status badges
├── autodoc/cli/                  # CLI documentation pages
│   ├── home.html                   # CLI root index (existing)
│   ├── command.html                # Command page ← NEW
│   ├── command-group.html          # Command group ← NEW
│   └── partials/
│       ├── options-table.html
│       ├── arguments-table.html
│       └── examples.html
├── partials/
│   ├── api-macros.html             # Shared API rendering macros ← NEW
│   └── ... (existing partials)
```

### Template Inheritance Pattern

All autodoc templates follow the same pattern as regular content:

```jinja2
{# themes/default/templates/autodoc/python/module.html #}
{% extends "autodoc/python/single.html" %}

{% block content %}
<div class="api-explorer">
  {% include 'autodoc/python/partials/module-header.html' %}

  {% for cls in classes %}
    {% include 'autodoc/python/partials/class-card.html' %}
  {% endfor %}

  {% for func in functions %}
    {% include 'autodoc/python/partials/function-card.html' %}
  {% endfor %}
</div>
{% endblock %}
```

Which extends:

```jinja2
{# themes/default/templates/autodoc/python/single.html #}
{% extends "base.html" %}

{% block content %}
<div class="docs-layout">
  <aside class="docs-sidebar">{% include 'partials/docs-nav.html' %}</aside>
  <main class="docs-main">
    {% include 'partials/page-hero.html' %}
    <article class="prose">
      {{ content | safe }}
    </article>
  </main>
  {% include 'partials/docs-toc-sidebar.html' %}
</div>
{% endblock %}
```

### Virtual Orchestrator Changes

The orchestrator renders element data directly to the page's `rendered_html`:

```python
# bengal/autodoc/virtual_orchestrator.py

def _render_module(self, element: DocElement) -> str:
    """Render module using theme template."""
    # Try theme template first
    try:
        template = self.template_env.get_template("autodoc/python/module.html")
        return template.render(
            element=element,
            classes=element.get_classes(),
            functions=element.get_functions(),
            config=self.config,
            site=self.site,
        )
    except TemplateNotFound:
        # Fall back to minimal built-in template
        return self._render_fallback(element)
```

### User Customization

Users can override any autodoc template in their custom theme:

```
my-site/
├── themes/
│   └── my-theme/
│       └── templates/
│           └── autodoc/python/
│               └── module.html    # Custom API module template
└── bengal.toml
```

Or add to the default theme via site-level templates:

```
my-site/
├── templates/
│   └── autodoc/python/
│       └── partials/
│           └── class-card.html    # Override just the class card
```

### Fallback Templates

A minimal set of fallback templates remain in autodoc for:
1. Sites without a theme
2. Themes that don't provide API templates
3. Standalone autodoc usage (rare)

```
bengal/autodoc/
└── fallback/
    ├── module.html      # Minimal, functional HTML
    ├── section.html
    └── README.md        # Explains fallback purpose
```

These are intentionally minimal (no styling, basic structure).

---

## Benefits

### For Users

1. **Consistent design** - API docs match site theme automatically
2. **Easy customization** - Override templates using familiar theme patterns
3. **Full theme access** - Use all theme CSS, JS, icons, macros
4. **Progressive disclosure** - Theme controls layout (sidebars, TOC, etc.)

### For Maintainers

1. **Single template system** - One architecture, one set of patterns
2. **Shared components** - Macros, partials work across all page types
3. **Clearer separation** - Autodoc = logic, Theme = presentation
4. **Easier testing** - Template tests in theme, logic tests in autodoc

### For Theme Authors

1. **API templates are opt-in** - Don't include them if not needed
2. **Full control** - Style API docs to match any design system
3. **Composable partials** - Mix and match components

---

## Migration Path

### Phase 1: Create Theme Templates (Non-breaking)

1. Add new templates to `themes/default/templates/autodoc/python/`
2. Add partials for reusable components
3. Update orchestrator to prefer theme templates
4. Keep existing `html_templates/` as fallback

### Phase 2: Deprecate Old Templates

1. Add deprecation notice to `autodoc/templates/` markdown files
2. Update documentation
3. Move `html_templates/` content to `fallback/`

### Phase 3: Remove Legacy (Major Version)

1. Remove `autodoc/templates/` (markdown-based)
2. Remove `autodoc/html_templates/`
3. Only keep `autodoc/fallback/` for edge cases

---

## Final Structure

### `bengal/autodoc/` (Post-Migration)

```
bengal/autodoc/
├── __init__.py
├── base.py                 # DocElement, metadata models
├── extractors/
│   ├── __init__.py
│   ├── python.py          # Python source extraction
│   ├── cli.py             # CLI command extraction
│   └── openapi.py         # OpenAPI spec extraction
├── virtual_orchestrator.py # Virtual page generation
├── cli_orchestrator.py    # CLI doc orchestration
├── generators/            # Legacy markdown generation (deprecated)
└── fallback/              # Minimal fallback templates
    ├── module.html
    ├── section.html
    └── README.md
```

### `themes/default/templates/` (Additions)

```
themes/default/templates/
├── autodoc/python/
│   ├── home.html              # Existing
│   ├── list.html              # Existing  
│   ├── single.html            # Existing (wrapper)
│   ├── module.html            # NEW: Python module
│   ├── section-index.html     # NEW: Package/section index
│   └── partials/              # NEW: API components
│       ├── class-card.html
│       ├── function-card.html
│       ├── method-item.html
│       ├── attributes-table.html
│       ├── parameters-table.html
│       ├── returns-section.html
│       ├── raises-list.html
│       ├── signature.html
│       ├── badges.html
│       └── examples.html
├── autodoc/cli/
│   ├── home.html              # Existing
│   ├── list.html              # Existing
│   ├── single.html            # Existing
│   ├── command.html           # NEW: CLI command
│   ├── command-group.html     # NEW: Command group
│   └── partials/              # NEW: CLI components
│       ├── options-table.html
│       ├── arguments-table.html
│       └── usage-block.html
└── partials/
    └── api-macros.html        # NEW: Shared macros
```

---

## Open Questions

1. **Should `autodoc/python/` become `api-explorer/`?**  
   Current naming is fine, but "explorer" emphasizes interactivity.

2. **How do we handle OpenAPI templates?**  
   Same pattern: `openapi/` directory with endpoint, schema templates.

3. **Should fallback templates be styled at all?**  
   Proposal: Minimal inline styles only, no CSS dependencies.

4. **Do we need a migration script for existing sites?**  
   Probably not - new templates won't break sites using markdown-based autodoc.

---

## Decision

**Recommendation**: Proceed with Phase 1 immediately. This is non-breaking and provides immediate value.

---

## Next Steps

1. [ ] Review and approve RFC
2. [ ] Create `autodoc/python/module.html` in theme
3. [ ] Create partials for class, function, method rendering
4. [ ] Update `virtual_orchestrator.py` template loading
5. [ ] Test with Bengal's own API documentation
6. [ ] Update documentation
7. [ ] Clean up files created in `autodoc/templates/html/`
