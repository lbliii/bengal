# RFC-003: Theme Inheritance Model

**Status**: ✅ Already Implemented → Documentation Task  
**Created**: 2024-12-08  
**Archived**: 2024-12-08  
**Part of**: [Theme Architecture Series](../active/rfc-theme-architecture-series.md)  

---

> **Why Archived**: Investigation revealed theme inheritance **already exists**:
> - `resolve_theme_chain()` in `environment.py:28-57`
> - Swizzle system in `utils/swizzle.py` (325 lines)
> - `bengal theme new --extends` CLI command
> - Max depth (5) already enforced
>
> **Action**: Convert to documentation task (DOC-001) instead of implementation RFC.  

---

## Summary

Introduce a parent-child theme inheritance model where child themes can extend a parent theme, overriding only specific templates, styles, or configuration.

---

## Problem Statement

### Current State

Theme inheritance is **partially implemented** but not exposed to users:

```python
# bengal/rendering/template_engine/environment.py:28-57
def resolve_theme_chain(active_theme: str | None, site: Any) -> list[str]:
    """
    Resolve theme inheritance chain starting from the active theme.
    Order: child first → parent → ... (do not duplicate 'default').
    """
    chain = []
    visited: set[str] = set()
    current = active_theme or "default"
    depth = 0
    MAX_DEPTH = 5  # Already enforced!

    while current and current not in visited and depth < MAX_DEPTH:
        visited.add(current)
        chain.append(current)
        extends = read_theme_extends(current, site)  # Reads theme.toml
        if not extends or extends == current:
            break
        current = extends
        depth += 1
    ...

# bengal/rendering/template_engine/environment.py:60-121
def read_theme_extends(theme_name: str, site: Any) -> str | None:
    """Read theme.toml for 'extends' value."""
    # Looks for theme.toml in site themes, installed packages, bundled themes
```

**Evidence**: Template resolution already searches theme chain (`environment.py:152-203`)

### What's Missing

1. **No theme.toml in default** - Feature exists but no themes use it
2. **No documentation** - Users don't know this capability exists
3. **Config inheritance** - Only templates resolve through chain, not config
4. **Asset inheritance** - Assets not yet resolved through chain

### What Already Exists (Swizzle System)

Bengal has a **complete swizzle system** for template customization:

```python
# bengal/utils/swizzle.py - SwizzleManager
class SwizzleManager:
    def swizzle(self, template_rel_path: str) -> Path:
        """Copy theme template to project templates/ with provenance tracking."""

    def list(self) -> list[SwizzleRecord]:
        """List all swizzled templates."""

    def update(self) -> dict[str, int]:
        """Update swizzled files from upstream if unchanged locally."""
```

**CLI Commands**:
```bash
bengal theme swizzle partials/header.html    # Copy to project
bengal theme swizzle-list                     # List swizzled files
bengal theme swizzle-update                   # Update from upstream
bengal theme discover                         # List swizzlable templates
```

**Provenance Tracking** (`.bengal/themes/sources.json`):
- Records source theme, checksums, timestamps
- Detects local modifications
- Safe update when unchanged

**Evidence**: `bengal/utils/swizzle.py:41-311`, `bengal/cli/commands/theme.py:27-115`

### Problems for Users

1. **Hidden feature** - Inheritance + swizzle work but aren't documented together
2. **Incomplete** - Templates yes, config/assets no
3. **Swizzle vs inheritance unclear** - When to use which approach

---

## Proposal

### Parent Theme Declaration

```yaml
# themes/my-company/theme.yaml
name: my-company
version: 1.0.0
parent: default  # Inherit from default theme

# Override only what's different
features:
  content:
    lightbox: false  # Disable lightbox

appearance:
  default_mode: dark
  default_palette: corporate

tokens:
  fonts:
    heading: "Inter, system-ui, sans-serif"
  colors:
    primary: "#0066cc"
```

### Directory Structure

```
themes/
├── default/                    # Parent theme
│   ├── theme.yaml
│   ├── assets/
│   ├── templates/
│   └── ...
└── my-company/                 # Child theme
    ├── theme.yaml              # parent: default
    ├── assets/
    │   └── css/
    │       └── overrides.css   # Additional styles
    └── templates/
        ├── partials/
        │   └── header.html     # Override header only
        └── content-types/
            └── docs/
                └── page.html   # Custom docs layout
```

### Resolution Order

For any resource (template, asset, config):

1. **Child theme** - `themes/my-company/templates/foo.html`
2. **Parent theme** - `themes/default/templates/foo.html`
3. **Built-in fallback** - Bengal's internal fallbacks

For deep inheritance:
```
grandchild → child → parent → default → fallback
```

### Template Inheritance

Child can extend parent's template:

```jinja2
{# themes/my-company/templates/layouts/base.html #}
{% extends "default::layouts/base.html" %}

{% block head_end %}
  {{ super() }}
  <link rel="stylesheet" href="{{ asset_url('css/overrides.css') }}">
{% endblock %}

{% block header %}
  {# Completely replace header #}
  <header class="corporate-header">
    <img src="/logo.svg" alt="Company">
    {{ super() }}  {# Include parent's header content #}
  </header>
{% endblock %}
```

The `default::` prefix explicitly references parent theme.

### Asset Inheritance

Assets merge with child taking precedence:

```python
def resolve_asset(path: str, theme_chain: list[Theme]) -> Path:
    """Resolve asset through theme chain."""
    for theme in theme_chain:  # child first
        asset_path = theme.path / "assets" / path
        if asset_path.exists():
            return asset_path
    raise AssetNotFoundError(path)
```

CSS can import parent:

```css
/* themes/my-company/assets/css/style.css */
@import url('default::css/style.css');

/* Overrides */
:root {
  --color-primary: #0066cc;
}
```

### Configuration Merge

Config deep-merges with child taking precedence:

```python
def merge_theme_config(parent: ThemeConfig, child: ThemeConfig) -> ThemeConfig:
    """Deep merge theme configurations."""
    merged = deep_merge(parent.to_dict(), child.to_dict())
    return ThemeConfig.from_dict(merged)
```

Example:
```yaml
# Parent (default)
features:
  navigation:
    back_to_top: true
    breadcrumbs: true
  content:
    lightbox: true

# Child (my-company)
features:
  content:
    lightbox: false  # Override this only

# Result
features:
  navigation:
    back_to_top: true    # Inherited
    breadcrumbs: true    # Inherited
  content:
    lightbox: false      # Overridden
```

### Theme Chain API

**Note**: Much of this already exists. `resolve_theme_chain()` in `environment.py` handles template resolution. The proposal adds config/asset resolution.

```python
# bengal/themes/resolver.py (proposed extension of existing code)

class ThemeChain:
    """Resolved theme inheritance chain."""

    def __init__(self, themes: list[Theme]):
        self.themes = themes  # [child, parent, grandparent, ...]

    @property
    def root(self) -> Theme:
        """The active (child) theme."""
        return self.themes[0]

    def resolve_template(self, name: str) -> Path:
        """Find template in chain. (ALREADY EXISTS in environment.py)"""
        for theme in self.themes:
            path = theme.templates_dir / name
            if path.exists():
                return path
        raise TemplateNotFound(name)

    def resolve_asset(self, name: str) -> Path:
        """Find asset in chain. (NEW - extend existing)"""
        ...

    @property
    def merged_config(self) -> ThemeConfig:
        """Merged configuration from all themes. (NEW)"""
        config = ThemeConfig.defaults()
        for theme in reversed(self.themes):  # parent first
            config = merge_theme_config(config, theme.config)
        return config


# ALREADY EXISTS: bengal/rendering/template_engine/environment.py:28-57
def resolve_theme_chain(active_theme: str | None, site: Any) -> list[str]:
    """Resolve theme inheritance chain starting from the active theme."""
    # ... implementation exists ...
```

### Integration with Swizzle System

The swizzle system (`bengal/utils/swizzle.py`) complements inheritance:

| Mechanism | Purpose | Scope |
|-----------|---------|-------|
| **Theme inheritance** | Reusable theme variants | Entire theme |
| **Swizzle** | One-off template customization | Single templates |

Swizzle already uses `_find_theme_template()` which respects the theme chain:

```python
# bengal/utils/swizzle.py:242-250
def _find_theme_template(self, template_rel_path: str) -> Path | None:
    engine = TemplateEngine(self.site)
    return engine._find_template_path(template_rel_path)  # Uses theme chain!
```

### Jinja2 Integration

Custom loader for theme chain:

```python
class ThemeChainLoader(BaseLoader):
    """Jinja2 loader that resolves through theme chain."""

    def __init__(self, theme_chain: ThemeChain):
        self.chain = theme_chain

    def get_source(self, environment, template):
        # Handle explicit parent reference: "default::layouts/base.html"
        if "::" in template:
            theme_name, path = template.split("::", 1)
            theme = self.chain.get_theme(theme_name)
            return self._load_from_theme(theme, path)

        # Normal resolution through chain
        for theme in self.chain.themes:
            try:
                return self._load_from_theme(theme, template)
            except TemplateNotFound:
                continue

        raise TemplateNotFound(template)
```

---

## Use Cases

### Inheritance vs Swizzle: When to Use Which

| Approach | Use When | Example |
|----------|----------|---------|
| **Theme Inheritance** | Creating a reusable theme variant | Corporate theme extending default |
| **Swizzle** | One-off customization for a single site | Customize just the header partial |
| **Both** | Theme + site-specific tweaks | Corporate theme + client logo |

### 1. Corporate Branding (Theme Inheritance)

Create a reusable corporate theme:

```yaml
# themes/acme-corp/theme.yaml
parent: default
appearance:
  default_palette: acme
tokens:
  fonts:
    heading: "Acme Sans"
```

Override: `themes/acme-corp/templates/partials/header.html` with company logo.

### 2. Site-Specific Customization (Swizzle)

For one-off changes without creating a full theme:

```bash
# Copy header from theme to project for customization
bengal theme swizzle partials/header.html

# Edit templates/partials/header.html with your changes

# Later: check for upstream updates
bengal theme swizzle-update
```

### 3. Combined Approach

Corporate theme + site-specific tweaks:

```yaml
# Site bengal.toml
[theme]
name = "acme-corp"  # Use inherited theme
```

```bash
# Swizzle one template for client-specific logo
bengal theme swizzle partials/footer.html
```

### 4. Language-Specific Theme

```yaml
# themes/rtl-arabic/theme.yaml
parent: default
tokens:
  direction: rtl
```

Override: CSS with RTL adjustments.

---

## Benefits

1. **Minimal override** - Change only what you need
2. **Update-safe** - Parent updates propagate automatically
3. **Composable** - Layer multiple extensions
4. **Explicit** - Clear what's inherited vs overridden
5. **Discoverable** - Child theme shows only differences

---

## Implementation

### Phase 1: Expose Existing Infrastructure
- [x] ~~Implement ThemeChain resolver~~ (exists: `resolve_theme_chain()`)
- [x] ~~Create ThemeChainLoader for Jinja2~~ (templates already resolve through chain)
- [x] ~~Max depth enforcement~~ (MAX_DEPTH=5 in environment.py)
- [ ] Add `parent` field to RFC-001's `theme.yaml` schema
- [ ] Document existing theme.toml `extends` key
- [ ] Add `theme_name::` prefix parsing for explicit parent refs

### Phase 2: Complete Asset Resolution
- [ ] Update `asset_url` to resolve through chain (templates done, assets not)
- [ ] Add CSS `@import` rewriting for parent refs
- [ ] Handle icon inheritance through chain

### Phase 3: Configuration Merge
- [ ] Extend `Theme.from_config()` to merge parent configs
- [ ] Deep merge feature flags from parent
- [ ] Merge design tokens from parent

### Phase 4: CLI & Tooling
- [x] ~~Add `bengal theme create --parent default`~~ (exists: `bengal theme new --extends default`)
- [ ] Add `bengal theme diff child parent`
- [ ] Add theme inheritance visualization
- [ ] Document existing swizzle commands alongside inheritance

### Phase 5: Documentation
- [ ] Document existing + new inheritance features
- [ ] Create "extending default theme" tutorial
- [ ] Add examples for common customizations

---

## Open Questions

1. **How deep can inheritance go?**  
   **Already implemented**: Max 5 levels in `resolve_theme_chain()` (`environment.py:45`)
   Proposal: Make configurable via site config

2. **Can a theme have multiple parents?**  
   **Already implemented**: No, single inheritance via `extends` in theme.toml
   Proposal: Keep single inheritance (simpler, already working)

3. **How to handle breaking parent changes?**  
   Proposal: Semver for themes, changelog for breaking changes

4. **Should we rename theme.toml to theme.yaml for consistency with RFC-001?**  
   Proposal: Support both, prefer theme.yaml for new themes
