# RFC-001: Theme Configuration Consolidation

**Status**: Draft  
**Created**: 2024-12-08  
**Part of**: [Theme Architecture Series](rfc-theme-architecture-series.md)  
**Priority**: High  
**Dependencies**: None  
**Note**: Includes icon config (merged from archived RFC-006)  

---

## Summary

Consolidate all theme configuration into a single `theme.yaml` file, replacing scattered configuration across `features.py`, component YAMLs, and `bengal.toml` overrides.

---

## Problem Statement

### Current State

Theme configuration is scattered across multiple locations:

```
bengal/themes/default/
├── features.py              # Python registry of feature flags (FeatureInfo dataclasses)
├── dev/components/*.yaml    # Component documentation (7 YAML files)
└── README.md                # Documents some settings

bengal/core/theme.py         # Theme dataclass loaded from site config
├── Theme.from_config()      # Reads [theme] section from bengal.toml

site/bengal.toml             # Site config has theme settings
├── [theme]
│   ├── name = "default"
│   ├── default_appearance = "system"
│   ├── default_palette = "snow-lynx"
│   └── features = [...]

themes/default/templates/base.html  # Inline JS config injection
├── window.BENGAL_THEME_DEFAULTS = {
│       appearance: '{{ site.theme_config.default_appearance }}',
│       palette: '{{ site.theme_config.default_palette }}'
│   }
```

**Evidence**:
- `bengal/themes/default/features.py:50-189` - Feature registry with 18 features
- `bengal/core/theme.py:14-134` - Theme dataclass definition
- `bengal/themes/default/templates/base.html:145-147` - JS config injection

### Problems

1. **No single source of truth** - Feature definitions in Python, settings in TOML, defaults in code
2. **Python file for feature registry** - `features.py` requires code knowledge to extend
3. **Undiscoverable** - Users must trace through 3+ files to understand available features
4. **Split responsibility** - Theme metadata in code, appearance in config, JS separately
5. **No theme-level defaults** - Features default from Python code, not theme config

---

## Proposal

### Single `theme.yaml` File

```yaml
# themes/default/theme.yaml

#===============================================================================
# Theme Metadata
#===============================================================================
name: default
version: 2.0.0
description: "Bengal's default documentation theme"
author: Bengal Team
license: MIT
parent: null  # For theme inheritance (see RFC-003)

#===============================================================================
# Feature Flags
# Enable/disable theme features. Site config can override.
#===============================================================================
features:
  # Navigation features
  navigation:
    back_to_top: true
    breadcrumbs: true
    toc_sidebar: true
    section_nav: true
    mobile_nav: true
    search_modal: true

  # Content features  
  content:
    lightbox: true
    code_copy: true
    code_highlighting: true
    heading_anchors: true
    external_link_icons: true

  # Accessibility features
  accessibility:
    skip_link: true
    focus_visible: true
    reduced_motion: true

  # Developer features
  dev:
    live_reload: true
    debug_mode: false

#===============================================================================
# Appearance
# Default visual settings. Users can override in localStorage.
#===============================================================================
appearance:
  default_mode: system        # light | dark | system
  default_palette: ""         # Named palette or empty for default
  available_palettes:         # Palettes users can switch to
    - ""                      # Default
    - ocean
    - forest
    - sunset

#===============================================================================
# Design Tokens
# Override CSS custom properties. Merged with tokens.css.
#===============================================================================
tokens:
  fonts:
    heading: "Outfit, system-ui, sans-serif"
    body: "system-ui, -apple-system, sans-serif"
    mono: "ui-monospace, 'Fira Code', monospace"

  breakpoints:
    sm: 640px
    md: 768px
    lg: 1024px
    xl: 1280px

  spacing:
    content_max_width: 65ch
    sidebar_width: 280px
    toc_width: 240px

#===============================================================================
# Icons
# Icon configuration (merged from RFC-006)
# Moves ICON_MAP from Python code to config
#===============================================================================
icons:
  library: phosphor           # Built-in: phosphor, heroicons, feather
  default_size: 20
  default_weight: regular     # For phosphor: thin, light, regular, bold, fill

  # Semantic aliases (currently hardcoded in _icons.py ICON_MAP)
  aliases:
    search: magnifying-glass
    menu: list
    close: x
    nav-menu: list
    nav-close: x
    external-link: arrow-square-out
    copy: clipboard
    success: check-circle
    warning: warning-circle
    error: x-circle
    info: info

#===============================================================================
# Assets
# Asset processing configuration.
#===============================================================================
assets:
  bundle_js: false            # Bundle all JS into single file
  bundle_css: false           # Bundle all CSS into single file
  minify: false               # Minify assets (production)

#===============================================================================
# Search
# Search feature configuration (moved from bengal.toml for theme control)
#===============================================================================
search:
  enabled: true
  preload: smart              # eager | lazy | smart
  max_results: 10
  highlight: true

#===============================================================================
# Templates
# Template-specific configuration.
#===============================================================================
templates:
  # Default template for content types
  defaults:
    page: layouts/page.html
    post: content-types/blog/article.html
    doc: content-types/docs/page.html

  # Template aliases (short names → full paths)
  aliases:
    blog: content-types/blog/article.html
    api: content-types/api-reference/module.html
```

### Loading Priority

1. Theme's `theme.yaml` (defaults)
2. Parent theme's `theme.yaml` (if inheritance)
3. Site's `bengal.toml` `[theme]` section (overrides)
4. Page frontmatter (page-level overrides)

### Python API

```python
# bengal/themes/config.py

@dataclass
class ThemeConfig:
    """Validated theme configuration."""
    name: str
    version: str
    parent: str | None
    features: FeatureFlags
    appearance: AppearanceConfig
    tokens: DesignTokens
    icons: IconConfig
    assets: AssetConfig
    search: SearchConfig
    templates: TemplateConfig

    @classmethod
    def load(cls, theme_path: Path) -> ThemeConfig:
        """Load and validate theme.yaml."""
        config_path = theme_path / "theme.yaml"
        if not config_path.exists():
            return cls.defaults()

        raw = yaml.safe_load(config_path.read_text())
        return cls.from_dict(raw)

    def merge_site_config(self, site_config: dict) -> ThemeConfig:
        """Merge site-level overrides."""
        # Deep merge site[theme] into self
        ...
```

### Template Access

```jinja2
{# Access theme config in templates #}
{% if theme.features.navigation.back_to_top %}
<button class="back-to-top">↑</button>
{% endif %}

{# Access tokens #}
<style>
  :root {
    --font-heading: {{ theme.tokens.fonts.heading }};
  }
</style>

{# Check feature with shorthand #}
{% if 'content.lightbox' | feature_enabled %}
  {% include 'partials/lightbox.html' %}
{% endif %}
```

### Migration from `features.py`

Current `features.py` uses dataclass registry:
```python
# bengal/themes/default/features.py:50-66
FEATURES: dict[str, FeatureInfo] = {
    "navigation.breadcrumbs": FeatureInfo(
        key="navigation.breadcrumbs",
        description="Show breadcrumb trail above content",
        default=True,
        category="navigation",
    ),
    "navigation.toc": FeatureInfo(
        key="navigation.toc",
        description="Show table of contents sidebar",
        default=True,
        category="navigation",
    ),
    # ... 16 more features
}
```

Becomes `theme.yaml`:
```yaml
features:
  navigation:
    breadcrumbs:
      enabled: true
      description: "Show breadcrumb trail above content"
    toc:
      enabled: true
      description: "Show table of contents sidebar"
  content:
    lightbox:
      enabled: true
      description: "Enable image lightbox on click"
```

Automated migration:
```bash
bengal theme migrate-config themes/default
# Reads features.py, generates theme.yaml, deprecates features.py
```

**Note**: The existing `Theme` dataclass in `bengal/core/theme.py` already handles feature loading from config. This RFC proposes moving the feature *definitions* (descriptions, defaults, categories) to YAML.

---

## Benefits

1. **Single source of truth** - All config in one file
2. **Discoverable** - Open `theme.yaml`, see all options
3. **Validatable** - Schema validation on load
4. **Documentable** - Comments inline with config
5. **Overridable** - Clear cascade: theme → site → page
6. **Type-safe** - Dataclass models with validation

---

## Breaking Changes

None. Existing configuration continues to work:

- `features.py` registry still loaded if present (deprecation warning)
- `bengal.toml` `[theme]` section unchanged
- `Theme.from_config()` in `bengal/core/theme.py` extended to support `theme.yaml`

### Existing Infrastructure to Leverage

The current codebase already has:
- `Theme` dataclass (`bengal/core/theme.py:14-134`)
- `Theme.from_config()` factory method
- Feature validation (`validate_features()` in `features.py:209-225`)
- Template access via `site.theme_config`

---

## Implementation

### Phase 1: Core
- [ ] Create `ThemeConfig` dataclass with validation
- [ ] Add `theme.yaml` loader
- [ ] Inject `theme` into template context
- [ ] Add `feature_enabled` filter

### Phase 2: Migration
- [ ] Create migration script for `features.py`
- [ ] Add deprecation warning for `features.py`
- [ ] Update default theme with `theme.yaml`

### Phase 3: Documentation
- [ ] Document `theme.yaml` schema
- [ ] Add theme configuration guide
- [ ] Update theme development docs

---

## Open Questions

1. **Should `theme.yaml` support TOML?**  
   Proposal: YAML only for themes, keeps distinction from `bengal.toml`

2. **How to handle theme-specific config keys?**  
   Proposal: `custom:` section for arbitrary theme data

3. **Should tokens directly generate CSS?**  
   Proposal: Yes, inject as `<style>` in head or generate `tokens.css`
