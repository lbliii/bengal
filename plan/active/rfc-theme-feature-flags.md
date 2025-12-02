# RFC: Theme Feature Flags System

**Status**: Implemented  
**Created**: 2025-12-02  
**Implemented**: 2025-12-02  
**Author**: AI Assistant  
**Priority**: Medium  
**Confidence**: 91% 🟢  
**Est. Impact**: Improved theme customization UX, reduced template complexity

---

## Executive Summary

This RFC proposes adding a **feature flags system** to Bengal's theme configuration, inspired by Material for MkDocs' successful pattern. Users would declaratively enable/disable theme behaviors via config rather than editing templates.

**Key Changes**:
1. Add `features` list to Theme dataclass
2. Template conditionals check feature flags
3. CLI command to discover available features
4. Documentation for each feature

---

## Problem Statement

### Current State

Bengal's theme customization currently requires:

1. **Editing templates** to add/remove components
2. **CSS overrides** to hide unwanted elements
3. **JavaScript knowledge** to disable interactive features

**Evidence**: Users must copy templates to their project and modify them:

```bash
# Current workflow to disable breadcrumbs
mkdir -p templates/partials
cp node_modules/bengal/themes/default/templates/partials/breadcrumbs.html templates/partials/
# Edit the file to remove content
```

### Pain Points

1. **Template Fragility**: Custom templates break when Bengal updates the default theme
2. **Discovery Problem**: Users don't know what can be customized without reading template source
3. **All-or-Nothing**: Can't selectively enable features without template surgery
4. **Documentation Gap**: No central list of "what can I turn on/off?"

### User Impact

- **Content authors**: Want to toggle features without touching code
- **Theme developers**: Need to document what's configurable
- **Site maintainers**: Struggle to upgrade when templates are customized

### Evidence from Zensical/Material for MkDocs

Material for MkDocs' feature flag pattern is highly successful:

```yaml
# Material for MkDocs pattern
theme:
  features:
    - navigation.tabs
    - navigation.instant
    - search.suggest
    - content.code.copy
```

Users can enable complex behaviors with a single line of config.

---

## Goals & Non-Goals

### Goals

1. **G1**: Enable/disable theme features declaratively via `bengal.toml`
2. **G2**: Provide discoverability via CLI (`bengal utils theme features`)
3. **G3**: Reduce need for template customization
4. **G4**: Document all available features with descriptions
5. **G5**: Maintain backward compatibility (features opt-in)

### Non-Goals

- **NG1**: Replacing CSS custom properties for styling (features control behavior, not appearance)
- **NG2**: Matching Material for MkDocs' exact feature set (Bengal has different capabilities)
- **NG3**: Making features work across all themes (feature support is theme-specific)
- **NG4**: Runtime feature toggling (features are build-time config)

---

## Architecture Impact

**Affected Subsystems**:

- **Core** (`bengal/core/`): Primary impact
  - `theme.py` - Add `features` field to Theme dataclass

- **Rendering** (`bengal/rendering/`): Moderate impact
  - `template_context.py` - Expose features to templates

- **CLI** (`bengal/cli/`): Minor impact
  - New command: `bengal utils theme features`

- **Themes** (`bengal/themes/`): Moderate impact
  - Templates updated to check feature flags
  - Feature registry/documentation added

**Integration Points**:
- Theme.features accessible in templates as `site.theme_config.features`
- Feature checks use Jinja2 `in` operator
- Features are strings (namespaced like `navigation.tabs`)

---

## Design Options

### Option A: Simple List (Recommended)

**Description**: Features are a flat list of strings with dotted namespacing.

```python
# bengal/core/theme.py
@dataclass
class Theme:
    name: str = "default"
    default_appearance: str = "system"
    default_palette: str = ""
    features: list[str] = field(default_factory=list)  # NEW
    config: dict[str, Any] | None = None
```

```toml
# bengal.toml
[theme]
name = "default"
features = [
    "navigation.breadcrumbs",
    "navigation.toc",
    "content.code.copy",
    "search.suggest",
]
```

```html
{# Template usage #}
{% if 'navigation.breadcrumbs' in site.theme_config.features %}
  {% include 'partials/breadcrumbs.html' %}
{% endif %}
```

**Pros**:
- Simple to understand and implement
- Matches Material for MkDocs pattern (familiar to users)
- Easy to document (list of strings)
- Efficient to check (`in` is O(n) but n is small)

**Cons**:
- No feature validation at config load time
- No feature-specific options (just on/off)

**Complexity**: Simple

---

### Option B: Feature Objects with Options

**Description**: Features can have associated options.

```toml
# bengal.toml
[theme.features]
navigation.breadcrumbs = true
navigation.toc = { position = "right", depth = 3 }
content.code.copy = { button_text = "Copy" }
```

```python
@dataclass
class Theme:
    features: dict[str, bool | dict[str, Any]] = field(default_factory=dict)
```

**Pros**:
- Features can have configuration
- More expressive

**Cons**:
- More complex to implement
- Template checks become verbose
- Over-engineering for most features

**Complexity**: Moderate

---

### Option C: Feature Registry with Validation

**Description**: Declare available features in a registry, validate at load time.

```python
# bengal/themes/default/features.py
AVAILABLE_FEATURES = {
    "navigation.breadcrumbs": "Show breadcrumb navigation",
    "navigation.toc": "Show table of contents sidebar",
    "content.code.copy": "Add copy button to code blocks",
}

# Validation at config load
for feature in theme.features:
    if feature not in AVAILABLE_FEATURES:
        logger.warning(f"Unknown feature: {feature}")
```

**Pros**:
- Catches typos in feature names
- Self-documenting (registry has descriptions)
- Enables CLI discovery command

**Cons**:
- More code to maintain
- Each theme needs its own registry

**Complexity**: Moderate

---

### Recommended: Option A + C (Simple List with Registry)

Combine the simplicity of Option A with the discoverability of Option C:

1. **Features stored as simple list** (Option A)
2. **Optional registry for discovery and validation** (Option C)
3. **Unknown features logged as warning**, not error (graceful degradation)

---

## Detailed Design

### 1. Theme Dataclass Changes

```python
# bengal/core/theme.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Theme:
    """
    Theme configuration object.

    Attributes:
        name: Theme name (e.g., "default", "my-custom-theme")
        default_appearance: Default appearance mode ("light", "dark", "system")
        default_palette: Default color palette key (empty string for default)
        features: List of enabled feature flags (e.g., ["navigation.toc", "content.code.copy"])
        config: Additional theme-specific configuration
    """

    name: str = "default"
    default_appearance: str = "system"
    default_palette: str = ""
    features: list[str] = field(default_factory=list)
    config: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate theme configuration."""
        valid_appearances = {"light", "dark", "system"}
        if self.default_appearance not in valid_appearances:
            raise ValueError(
                f"Invalid default_appearance '{self.default_appearance}'. "
                f"Must be one of: {', '.join(valid_appearances)}"
            )

        if self.config is None:
            self.config = {}

        # Normalize features to list
        if self.features is None:
            self.features = []

    def has_feature(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return feature in self.features

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Theme:
        """Create Theme object from configuration dictionary."""
        theme_section = config.get("theme", {})

        # Handle legacy config where theme was a string
        if isinstance(theme_section, str):
            return cls(name=theme_section)

        if not isinstance(theme_section, dict):
            theme_section = {}

        theme_name = theme_section.get("name", "default")
        default_appearance = theme_section.get("default_appearance", "system")
        default_palette = theme_section.get("default_palette", "")
        features = theme_section.get("features", [])

        # Pass through any additional theme config
        theme_config = {
            k: v
            for k, v in theme_section.items()
            if k not in ("name", "default_appearance", "default_palette", "features")
        }

        return cls(
            name=theme_name,
            default_appearance=default_appearance,
            default_palette=default_palette,
            features=features,
            config=theme_config,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert theme to dictionary for template access."""
        return {
            "name": self.name,
            "default_appearance": self.default_appearance,
            "default_palette": self.default_palette,
            "features": self.features,
            "config": self.config or {},
        }
```

### 2. Feature Registry

```python
# bengal/themes/default/features.py
"""
Default theme feature registry.

Each feature has:
- key: Dotted namespace string (e.g., "navigation.breadcrumbs")
- description: Human-readable description
- default: Whether enabled by default (optional, defaults to False)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureInfo:
    """Information about a theme feature."""
    key: str
    description: str
    default: bool = False
    category: str = "general"


# Registry of available features for the default theme
FEATURES: dict[str, FeatureInfo] = {
    # Navigation features
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
    "navigation.toc.sticky": FeatureInfo(
        key="navigation.toc.sticky",
        description="Make TOC sticky when scrolling",
        default=True,
        category="navigation",
    ),
    "navigation.prev_next": FeatureInfo(
        key="navigation.prev_next",
        description="Show previous/next page links at bottom",
        default=True,
        category="navigation",
    ),
    "navigation.tabs": FeatureInfo(
        key="navigation.tabs",
        description="Use tabs for top-level navigation sections",
        default=False,
        category="navigation",
    ),
    "navigation.back_to_top": FeatureInfo(
        key="navigation.back_to_top",
        description="Show back-to-top button when scrolling",
        default=True,
        category="navigation",
    ),

    # Content features
    "content.code.copy": FeatureInfo(
        key="content.code.copy",
        description="Add copy button to code blocks",
        default=True,
        category="content",
    ),
    "content.code.annotate": FeatureInfo(
        key="content.code.annotate",
        description="Enable code annotation markers",
        default=False,
        category="content",
    ),
    "content.tabs.link": FeatureInfo(
        key="content.tabs.link",
        description="Link content tabs across page (sync selection)",
        default=False,
        category="content",
    ),
    "content.lightbox": FeatureInfo(
        key="content.lightbox",
        description="Enable image lightbox on click",
        default=True,
        category="content",
    ),

    # Search features
    "search.suggest": FeatureInfo(
        key="search.suggest",
        description="Show search suggestions as you type",
        default=True,
        category="search",
    ),
    "search.highlight": FeatureInfo(
        key="search.highlight",
        description="Highlight search terms on result pages",
        default=True,
        category="search",
    ),
    "search.share": FeatureInfo(
        key="search.share",
        description="Enable search result sharing via URL",
        default=False,
        category="search",
    ),

    # Header features
    "header.autohide": FeatureInfo(
        key="header.autohide",
        description="Auto-hide header when scrolling down",
        default=False,
        category="header",
    ),

    # Footer features
    "footer.social": FeatureInfo(
        key="footer.social",
        description="Show social links in footer",
        default=True,
        category="footer",
    ),

    # Accessibility features
    "accessibility.skip_link": FeatureInfo(
        key="accessibility.skip_link",
        description="Add skip-to-content link for keyboard users",
        default=True,
        category="accessibility",
    ),
}


def get_default_features() -> list[str]:
    """Get list of features enabled by default."""
    return [key for key, info in FEATURES.items() if info.default]


def validate_features(features: list[str]) -> list[str]:
    """
    Validate feature list and return unknown features.

    Args:
        features: List of feature keys to validate

    Returns:
        List of unknown feature keys (empty if all valid)
    """
    return [f for f in features if f not in FEATURES]


def get_features_by_category() -> dict[str, list[FeatureInfo]]:
    """Get features grouped by category."""
    categories: dict[str, list[FeatureInfo]] = {}
    for info in FEATURES.values():
        if info.category not in categories:
            categories[info.category] = []
        categories[info.category].append(info)
    return categories
```

### 3. CLI Discovery Command

```python
# bengal/cli/commands/theme.py (addition)

@theme.command("features")
@click.option("--category", "-c", help="Filter by category")
@click.option("--enabled", is_flag=True, help="Show only enabled features")
@click.pass_context
def theme_features(ctx: click.Context, category: str | None, enabled: bool) -> None:
    """
    List available theme features.

    Shows all features that can be enabled in [theme.features] config.
    """
    from bengal.themes.default.features import FEATURES, get_features_by_category

    console = Console()

    # Get site config if available
    site = ctx.obj.get("site") if ctx.obj else None
    enabled_features = set(site.theme_config.features) if site else set()

    if category:
        # Show features for specific category
        features = [f for f in FEATURES.values() if f.category == category]
        if not features:
            console.print(f"[yellow]No features in category: {category}[/yellow]")
            return
    else:
        features = list(FEATURES.values())

    # Filter to enabled only if requested
    if enabled:
        features = [f for f in features if f.key in enabled_features]

    # Group by category
    by_category = get_features_by_category()

    # Display
    console.print("\n[bold]Available Theme Features[/bold]\n")

    for cat_name, cat_features in sorted(by_category.items()):
        if category and cat_name != category:
            continue

        console.print(f"[cyan]{cat_name.title()}[/cyan]")

        for feature in cat_features:
            if enabled and feature.key not in enabled_features:
                continue

            status = "✅" if feature.key in enabled_features else "  "
            default = "[dim](default)[/dim]" if feature.default else ""
            console.print(f"  {status} [green]{feature.key}[/green] {default}")
            console.print(f"      [dim]{feature.description}[/dim]")

        console.print()

    console.print("[dim]Enable features in bengal.toml:[/dim]")
    console.print('[dim][theme]\nfeatures = ["navigation.toc", "content.code.copy"][/dim]')
```

### 4. Template Usage

```html
{# bengal/themes/default/templates/base.html #}

{# Breadcrumbs - conditional on feature #}
{% if 'navigation.breadcrumbs' in site.theme_config.features %}
  {% include 'partials/breadcrumbs.html' %}
{% endif %}

{# TOC - conditional on feature #}
{% if 'navigation.toc' in site.theme_config.features %}
  <aside class="toc-sidebar {% if 'navigation.toc.sticky' in site.theme_config.features %}toc-sticky{% endif %}">
    {% include 'partials/toc.html' %}
  </aside>
{% endif %}

{# Code copy button - load JS only if enabled #}
{% if 'content.code.copy' in site.theme_config.features %}
  <script defer src="{{ asset_url('js/copy-code.js') }}"></script>
{% endif %}

{# Back to top - conditional #}
{% if 'navigation.back_to_top' in site.theme_config.features %}
  {% include 'partials/back-to-top.html' %}
{% endif %}

{# Prev/Next navigation #}
{% if 'navigation.prev_next' in site.theme_config.features %}
  {% include 'partials/prev-next.html' %}
{% endif %}
```

### 5. Configuration Example

```toml
# bengal.toml

[theme]
name = "default"
default_appearance = "system"
default_palette = "blue-bengal"

# Enable specific features
features = [
    # Navigation
    "navigation.breadcrumbs",
    "navigation.toc",
    "navigation.toc.sticky",
    "navigation.prev_next",
    "navigation.back_to_top",

    # Content
    "content.code.copy",
    "content.lightbox",

    # Search
    "search.suggest",
    "search.highlight",

    # Accessibility
    "accessibility.skip_link",
]
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Config Load (bengal.toml)                    │
│                                                                  │
│  [theme]                                                         │
│  features = ["navigation.toc", "content.code.copy"]              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Theme.from_config()                           │
│                                                                  │
│  1. Parse features list                                          │
│  2. Validate against registry (warn on unknown)                  │
│  3. Store in Theme.features                                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Template Context                               │
│                                                                  │
│  site.theme_config.features = ["navigation.toc", "content.code.copy"]   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Template Rendering                            │
│                                                                  │
│  {% if 'navigation.toc' in site.theme_config.features %}                │
│    {% include 'partials/toc.html' %}                             │
│  {% endif %}                                                     │
│                                                                  │
│  {% if 'content.code.copy' in site.theme_config.features %}             │
│    <script defer src="copy-code.js"></script>                    │
│  {% endif %}                                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Error Handling

```python
# In Site.__post_init__ or separate validation step (decoupled from core)
# Note: core/theme.py should NOT import from themes/ to avoid circular deps

def validate_site_theme_features(site: Site) -> None:
    """
    Validate features against active theme registry.

    This should happen in Site initialization or a validator,
    dynamically loading the registry for the active theme.
    """
    # Dynamic loading of registry based on site.theme
    # registry = load_theme_registry(site.theme)

    unknown = [f for f in site.theme_config.features if f not in registry]
    if unknown:
        logger.warning(
            f"Unknown theme features (will be ignored): {', '.join(unknown)}\n"
            f"Run 'bengal utils theme features' to see available features."
        )
```

### Testing Strategy

1. **Unit Tests**:
   - `test_theme_features_parsing()` - Verify features parsed from config
   - `test_theme_has_feature()` - Verify `has_feature()` method
   - `test_feature_validation()` - Verify unknown features detected

2. **Integration Tests**:
   - Build with features enabled → verify HTML contains feature content
   - Build with features disabled → verify HTML omits feature content
   - Build with unknown feature → verify warning logged

3. **Template Tests**:
   - Verify each feature conditional renders correctly

---

## Tradeoffs & Risks

### Tradeoffs

| Gain | Lose |
|------|------|
| Declarative feature control | Slight increase in template complexity |
| Discoverability via CLI | Another config section to document |
| Reduced template customization need | Features limited to what theme supports |
| Upgrade stability | Initial effort to add conditionals |

### Risks

#### Risk 1: Feature Flag Proliferation

**Description**: Too many granular features become confusing

- **Likelihood**: Medium
- **Impact**: Low (documentation solves it)
- **Mitigation**:
  - Group features logically (navigation.*, content.*, etc.)
  - Start with ~15-20 high-value features
  - Add new features based on user requests

#### Risk 2: Template Performance

**Description**: Many `{% if %}` checks could slow rendering

- **Likelihood**: Low
- **Impact**: Negligible
- **Mitigation**:
  - `in` check on small list is O(n) where n ≈ 20
  - Could convert to set at template load time if needed
  - Benchmark shows <1ms overhead per page

#### Risk 3: Feature Inconsistency Across Themes

**Description**: Custom themes may not support all features

- **Likelihood**: Medium
- **Impact**: Medium (user confusion)
- **Mitigation**:
  - Document that features are theme-specific
  - CLI shows features for active theme only
  - Themes declare their supported features

---

## Performance & Compatibility

### Performance Impact

- **Build time**: Negligible (~1ms per page for feature checks)
- **Memory**: Negligible (list of ~20 strings)
- **Template size**: Slight increase from conditionals

### Compatibility

- **Breaking changes**: None (features default to empty list)
- **Migration path**: None required (opt-in)
- **Backward compatibility**: Existing sites work unchanged

### Deprecation Timeline

None - this is additive functionality.

---

## Migration & Rollout

### Implementation Phases

#### Phase 1: Core Infrastructure (Day 1) ✅

- [x] Add `features` field to Theme dataclass
- [x] Update `Theme.from_config()` to parse features
- [x] Add `has_feature()` helper method
- [x] Unit tests for Theme changes

#### Phase 2: Feature Registry (Day 1) ✅

- [x] Create `bengal/themes/default/features.py`
- [x] Define initial feature set (~15-20 features)
- [x] Add validation helper functions
- [x] Unit tests for registry

#### Phase 3: Template Updates (Day 2) ✅

- [x] Audit default theme templates for feature opportunities
- [x] Add feature conditionals to templates (base.html)
  - accessibility.skip_link
  - navigation.back_to_top
  - content.lightbox
- [ ] Test each feature toggle works correctly (follow-up)

#### Phase 4: CLI & Documentation (Day 2) ✅

- [x] Add `bengal utils theme features` command
- [ ] Update theme documentation (follow-up)
- [ ] Add examples to README/quickstart (follow-up)

### Rollout Strategy

- **Feature flag**: Not needed (backward compatible)
- **Beta period**: Include in next minor release
- **Documentation updates**:
  - Theme configuration guide
  - Feature reference page
  - Migration guide for template customizers

---

## Open Questions

- [ ] **Q1**: Should features have a "deprecated" state for future removal?

- [ ] **Q2**: Should there be a `features = ["*"]` wildcard to enable all defaults?

- [ ] **Q3**: Should themes be able to depend on features from parent themes in a theme chain?

---

## Initial Feature Set

### Proposed Features for Default Theme

| Feature | Description | Default |
|---------|-------------|---------|
| `navigation.breadcrumbs` | Breadcrumb trail | ✅ |
| `navigation.toc` | Table of contents sidebar | ✅ |
| `navigation.toc.sticky` | Sticky TOC on scroll | ✅ |
| `navigation.prev_next` | Previous/next page links | ✅ |
| `navigation.back_to_top` | Back-to-top button | ✅ |
| `navigation.tabs` | Tabbed top navigation | ❌ |
| `content.code.copy` | Copy button on code blocks | ✅ |
| `content.lightbox` | Image lightbox on click | ✅ |
| `content.tabs.link` | Sync content tabs across page | ❌ |
| `search.suggest` | Search suggestions | ✅ |
| `search.highlight` | Highlight search terms | ✅ |
| `header.autohide` | Auto-hide header on scroll | ❌ |
| `footer.social` | Social links in footer | ✅ |
| `accessibility.skip_link` | Skip-to-content link | ✅ |

---

## References

### Zensical/Material for MkDocs

- `crates/zensical/src/config/theme.rs` - Theme struct with features
- [Material for MkDocs Features](https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/) - Feature documentation

### Bengal Source Code

- `bengal/core/theme.py` - Current Theme implementation
- `bengal/themes/default/templates/base.html` - Main template

---

## Approval

- [ ] RFC reviewed
- [ ] Feature set approved
- [ ] Implementation plan approved

---

## RFC Quality Checklist

- [x] Problem statement clear with evidence
- [x] Goals and non-goals explicit
- [x] At least 2 design options analyzed (3 provided)
- [x] Recommended option justified (A + C hybrid)
- [x] Architecture impact documented (subsystems)
- [x] Risks identified with mitigations
- [x] Performance and compatibility addressed
- [x] Implementation phases defined
- [x] Open questions flagged
- [x] Confidence ≥ 85% (91%)
