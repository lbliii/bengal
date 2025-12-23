# RFC: Content-Aware CSS Tree Shaking

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-23  
**Subsystems**: orchestration/asset, themes/default, core/asset

---

## Executive Summary

Implement build-time CSS optimization that analyzes which content types are actually used in a site and generates a minimal `style.css` containing only the CSS needed for those types.

**Impact**: 50%+ CSS bundle reduction for single-purpose sites (blog-only, docs-only, recipe-only).

**Zero dependencies**: Pure Python implementation using Bengal's existing CSS bundler.

---

## Problem Statement

### Current Behavior

Bengal's default theme ships **all CSS** regardless of what content types a site uses:

```
themes/default/assets/css/style.css
├── tokens/         (~8KB)   - Always needed
├── base/           (~12KB)  - Always needed  
├── utilities/      (~4KB)   - Always needed
├── components/     (~120KB) - MOST NOT NEEDED for single-type sites
│   ├── blog.css           - Only for blogs
│   ├── autodoc.css        - Only for API docs
│   ├── tutorial.css       - Only for tutorials
│   ├── wiki.css           - Only for wikis (NEW)
│   ├── recipe.css         - Only for recipes (NEW)
│   └── ... 40+ more files
├── layouts/        (~15KB)  - Partially needed
└── pages/          (~8KB)   - Partially needed

TOTAL: ~180KB (minified: ~140KB, gzipped: ~25KB)
```

### The Problem

A **blog-only site** ships CSS for:
- ❌ `autodoc.css` (API documentation)
- ❌ `tutorial.css` (learning content)
- ❌ `docs-nav.css` (documentation sidebar)
- ❌ `tracks.css` (learning paths)
- ❌ `wiki.css` (knowledge base)
- ❌ `recipe.css` (cookbook)
- ❌ ... and 30+ other unused component files

**Result**: Users pay bandwidth/parse cost for CSS they'll never use.

### Why This Matters More Now

With the addition of specialized site types (RFC: `rfc-specialized-site-types.md`), we're adding:
- `portfolio.css`
- `product.css`
- `wiki.css`
- `recipe.css`
- `landing.css`

Without tree shaking, the CSS bundle will grow to ~200KB+. A recipe site shouldn't ship portfolio CSS.

---

## Goals

### Must Have
1. **Automatic detection** of content types used in site
2. **Build-time CSS filtering** - generate optimized style.css
3. **Zero config** - works out of the box
4. **No external dependencies** - pure Python

### Should Have
5. **Feature detection** - also filter by features (graph, search, mermaid)
6. **Logging** - show what was included/excluded
7. **Override mechanism** - force include/exclude specific CSS

### Nice to Have
8. **Size reporting** - show before/after bundle size
9. **Dev mode bypass** - option to include all CSS during development
10. **Per-page CSS** - load type-specific CSS only on matching pages

### Non-Goals
- Runtime CSS loading (adds complexity, HTTP requests)
- Selector-level tree shaking (requires PurgeCSS)
- CSS-in-JS or CSS modules

---

## Design

### Architecture Overview

```
Build Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Content Discovery
    └─► site.pages populated with all pages
    └─► site.sections populated with all sections

Phase 12.5: CSS Optimization (NEW)
    ├─► Scan pages for content types used
    ├─► Check features enabled
    ├─► Generate optimized style.css
    └─► Write to theme assets directory (temp)

Phase 13: Asset Processing
    └─► Bundle CSS (uses optimized style.css)
    └─► Minify, fingerprint, output
```

### CSS Manifest Structure

```python
# bengal/themes/default/css_manifest.py

"""
CSS manifest defining core, shared, and type-specific stylesheets.

Categories:
    CORE: Always included (tokens, base, essential layout)
    SHARED: Common components used across most types
    TYPE_MAP: Content-type-specific CSS
    FEATURE_MAP: Feature-specific CSS (graph, search, etc.)
"""

# ============================================
# CORE - Always included (site won't render without these)
# ============================================
CSS_CORE: list[str] = [
    # Design tokens (CSS custom properties)
    "tokens/foundation.css",
    "tokens/typography.css",
    "tokens/semantic.css",

    # Base styles (reset, typography, utilities)
    "base/reset.css",
    "base/typography.css",
    "base/utilities.css",
    "base/interactive-patterns.css",
    "base/accessibility.css",
    "base/print.css",

    # Utilities
    "utilities/motion.css",
    "utilities/scroll-animations.css",
    "utilities/gradient-borders.css",
    "utilities/fluid-blobs.css",

    # Core layout (every page needs these)
    "composition/layouts.css",
    "layouts/grid.css",
    "layouts/header.css",
    "layouts/footer.css",
    "layouts/page-header.css",
]

# ============================================
# SHARED - Common components (most sites need these)
# ============================================
CSS_SHARED: list[str] = [
    # UI primitives
    "components/buttons.css",
    "components/forms.css",
    "components/cards.css",
    "components/badges.css",
    "components/labels.css",
    "components/icons.css",
    "components/alerts.css",

    # Content components
    "components/admonitions.css",
    "components/tabs.css",
    "components/dropdowns.css",
    "components/code.css",
    "components/target-anchor.css",

    # Navigation
    "components/navigation.css",
    "components/pagination.css",
    "components/toc.css",
]

# ============================================
# TYPE-SPECIFIC - Only loaded when type is used
# ============================================
CSS_TYPE_MAP: dict[str, list[str]] = {
    # Blog & Archive
    "blog": [
        "components/blog.css",
        "components/archive.css",
        "components/author.css",
        "components/author-page.css",
        "components/related-posts.css",
        "components/share.css",
        "components/meta.css",
        "components/tags.css",
        "components/category-browser.css",
    ],

    # Documentation
    "doc": [
        "components/docs-nav.css",
        "components/action-bar.css",
        "components/nav-action-buttons.css",
        "components/versioning.css",
        "components/steps.css",
        "components/checklist.css",
    ],

    # Tutorials & Learning
    "tutorial": [
        "components/tutorial.css",
        "components/steps.css",
        "components/checklist.css",
    ],

    # Tracks (learning paths)
    "track": [
        "components/tracks.css",
        "components/hub-cards.css",
    ],

    # API Documentation
    "autodoc-python": [
        "components/autodoc.css",
        "components/reference-docs.css",
        "components/api-hub.css",
    ],
    "autodoc-cli": [
        "components/autodoc.css",
        "components/reference-docs.css",
    ],

    # Changelog
    "changelog": [
        "layouts/changelog.css",
    ],

    # Resume
    "resume": [
        "layouts/resume.css",
    ],

    # Landing pages
    "landing": [
        "pages/landing.css",
        "components/hero.css",
        "components/page-hero.css",
    ],

    # Portfolio (NEW - from rfc-specialized-site-types)
    "portfolio": [
        "components/portfolio.css",
    ],

    # Product/Catalog (NEW)
    "product": [
        "components/product.css",
    ],

    # Wiki (NEW)
    "wiki": [
        "components/wiki.css",
    ],

    # Recipe (NEW)
    "recipe": [
        "components/recipe.css",
        "layouts/recipe.css",  # Print styles
    ],
}

# ============================================
# FEATURE-SPECIFIC - Based on site.features config
# ============================================
CSS_FEATURE_MAP: dict[str, list[str]] = {
    "graph": [
        "components/graph.css",
        "components/graph-minimap.css",
        "components/graph-contextual.css",
    ],
    "search": [
        "components/search.css",
        "components/search-modal.css",
    ],
    "mermaid": [
        "components/mermaid.css",
    ],
    "data_tables": [
        "components/data-table.css",
        "tabulator.min.css",
    ],
    "interactive": [
        "components/interactive.css",
        "components/widgets.css",
    ],
}

# ============================================
# PALETTES - Color theme presets
# ============================================
CSS_PALETTES: list[str] = [
    "tokens/palettes/snow-lynx.css",
    "tokens/palettes/brown-bengal.css",
    "tokens/palettes/silver-bengal.css",
    "tokens/palettes/charcoal-bengal.css",
    "tokens/palettes/blue-bengal.css",
]
```

### CSS Optimizer Implementation

```python
# bengal/orchestration/css_optimizer.py

"""
Content-aware CSS tree shaking.

Analyzes site content to determine which CSS files are needed,
then generates an optimized style.css with only necessary imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.logging import get_logger

if TYPE_CHECKING:
    from bengal.core import Site

logger = get_logger(__name__)


class CSSOptimizer:
    """
    Generates optimized CSS bundles based on site content.

    Analyzes pages and sections to detect:
    - Content types in use (blog, doc, tutorial, etc.)
    - Features enabled (graph, search, mermaid, etc.)

    Then generates a minimal style.css containing only needed imports.

    Attributes:
        site: Site instance to analyze
        manifest_path: Path to CSS manifest (css_manifest.py)

    Example:
        optimizer = CSSOptimizer(site)
        optimized_css = optimizer.generate()

        # Or with reporting
        optimized_css, report = optimizer.generate(report=True)
        print(f"Included {report['included_count']} of {report['total_count']} CSS files")
    """

    def __init__(self, site: Site) -> None:
        self.site = site
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        """Load CSS manifest from theme."""
        # Import from theme's css_manifest.py
        # Falls back to default if theme doesn't have one
        try:
            from bengal.themes.default.css_manifest import (
                CSS_CORE,
                CSS_SHARED,
                CSS_TYPE_MAP,
                CSS_FEATURE_MAP,
                CSS_PALETTES,
            )
            return {
                "core": CSS_CORE,
                "shared": CSS_SHARED,
                "type_map": CSS_TYPE_MAP,
                "feature_map": CSS_FEATURE_MAP,
                "palettes": CSS_PALETTES,
            }
        except ImportError:
            logger.warning("css_manifest_not_found", theme=self.site.theme)
            return {}

    def get_used_content_types(self) -> set[str]:
        """
        Scan site to find all content types in use.

        Checks:
        - page.metadata.type for each page
        - section.metadata.content_type for each section

        Returns:
            Set of content type names (e.g., {"blog", "doc"})
        """
        types: set[str] = set()

        for page in self.site.pages:
            if page_type := page.metadata.get("type"):
                types.add(page_type)

        for section in self.site.sections:
            if ct := section.metadata.get("content_type"):
                types.add(ct)

        logger.debug("css_types_detected", types=sorted(types))
        return types

    def get_enabled_features(self) -> set[str]:
        """
        Detect features that require CSS.

        Checks:
        - site.config.features for explicit config
        - Content patterns (e.g., ```mermaid blocks)

        Returns:
            Set of feature names (e.g., {"search", "graph"})
        """
        features: set[str] = set()

        # Check explicit config
        feature_config = self.site.config.get("features", {})
        for feature, enabled in feature_config.items():
            if enabled:
                features.add(feature)

        # Auto-detect from content (sample first 100 pages for performance)
        sample_pages = list(self.site.pages)[:100]
        for page in sample_pages:
            content = getattr(page, "content", "") or ""

            if "```mermaid" in content:
                features.add("mermaid")

            # Wiki-style links suggest graph feature
            if "[[" in content and "]]" in content:
                features.add("graph")

        logger.debug("css_features_detected", features=sorted(features))
        return features

    def get_required_css_files(self) -> list[str]:
        """
        Determine which CSS files are needed.

        Combines:
        - Core CSS (always)
        - Shared CSS (always)
        - Type-specific CSS (based on content types)
        - Feature-specific CSS (based on features)
        - Palettes (all or just active)

        Returns:
            Ordered list of CSS file paths (relative to css/ directory)
        """
        if not self._manifest:
            # No manifest = include everything (fallback)
            return []

        imports: list[str] = []

        # 1. Core - always included
        imports.extend(self._manifest.get("core", []))

        # 2. Palettes
        palettes = self._manifest.get("palettes", [])
        include_all_palettes = self.site.config.get("css", {}).get("all_palettes", True)

        if include_all_palettes:
            imports.extend(palettes)
        else:
            # Only active palette
            active = self.site.config.get("theme", {}).get("palette", "blue-bengal")
            matching = [p for p in palettes if active in p]
            imports.extend(matching or palettes[:1])  # Fallback to first

        # 3. Shared - common components
        imports.extend(self._manifest.get("shared", []))

        # 4. Type-specific
        used_types = self.get_used_content_types()
        type_map = self._manifest.get("type_map", {})

        for content_type in used_types:
            if css_files := type_map.get(content_type):
                imports.extend(css_files)

        # 5. Feature-specific
        enabled_features = self.get_enabled_features()
        feature_map = self._manifest.get("feature_map", {})

        for feature in enabled_features:
            if css_files := feature_map.get(feature):
                imports.extend(css_files)

        # 6. Force-include from config
        force_include = self.site.config.get("css", {}).get("include", [])
        imports.extend(force_include)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for css_file in imports:
            if css_file not in seen:
                seen.add(css_file)
                unique.append(css_file)

        return unique

    def generate(self, report: bool = False) -> str | tuple[str, dict[str, Any]]:
        """
        Generate optimized style.css content.

        Args:
            report: If True, also return optimization report

        Returns:
            CSS content string, or tuple of (css_content, report_dict)
        """
        imports = self.get_required_css_files()

        if not imports:
            # No manifest or empty = return empty (use original style.css)
            logger.info("css_optimization_skipped", reason="no_manifest")
            if report:
                return "", {"skipped": True}
            return ""

        # Layer mapping for proper cascade
        layer_map = {
            "tokens/": "tokens",
            "base/": "base",
            "utilities/": "utilities",
            "composition/": "base",
            "layouts/": "pages",
            "components/": "components",
            "pages/": "pages",
        }

        # Generate CSS
        lines = [
            "/* Bengal SSG - Optimized CSS Bundle */",
            "/* Auto-generated based on content types detected */",
            "",
            "@layer tokens, base, utilities, components, pages;",
            "",
        ]

        for css_file in imports:
            # Determine layer
            layer = "components"  # default
            for prefix, layer_name in layer_map.items():
                if css_file.startswith(prefix):
                    layer = layer_name
                    break

            lines.append(f"@layer {layer} {{ @import url('{css_file}'); }}")

        css_content = "\n".join(lines)

        # Build report
        if report:
            all_files = self._get_all_css_files()
            excluded = set(all_files) - set(imports)

            report_data = {
                "included_count": len(imports),
                "excluded_count": len(excluded),
                "total_count": len(all_files),
                "reduction_percent": round(len(excluded) / max(len(all_files), 1) * 100),
                "types_detected": sorted(self.get_used_content_types()),
                "features_detected": sorted(self.get_enabled_features()),
                "included_files": imports,
                "excluded_files": sorted(excluded),
            }

            logger.info(
                "css_optimization_complete",
                included=report_data["included_count"],
                excluded=report_data["excluded_count"],
                reduction=f"{report_data['reduction_percent']}%",
            )

            return css_content, report_data

        return css_content

    def _get_all_css_files(self) -> list[str]:
        """Get list of all CSS files in manifest."""
        all_files: list[str] = []

        all_files.extend(self._manifest.get("core", []))
        all_files.extend(self._manifest.get("shared", []))
        all_files.extend(self._manifest.get("palettes", []))

        for css_list in self._manifest.get("type_map", {}).values():
            all_files.extend(css_list)

        for css_list in self._manifest.get("feature_map", {}).values():
            all_files.extend(css_list)

        return list(set(all_files))


def optimize_css_for_site(site: Site) -> str:
    """
    Convenience function to generate optimized CSS.

    Args:
        site: Site instance

    Returns:
        Optimized CSS content (empty string if optimization not applicable)
    """
    optimizer = CSSOptimizer(site)
    return optimizer.generate()
```

### Integration Point

```python
# bengal/orchestration/build/rendering.py (modified)

def phase_assets(
    orchestrator: BuildOrchestrator,
    cli: CLIOutput,
    incremental: bool,
    parallel: bool,
    assets_to_process: list[Asset],
    collector: OutputCollector | None = None,
) -> list[Asset]:
    """Phase 13: Process Assets."""

    # NEW: Generate optimized CSS before bundling
    if orchestrator.site.config.get("css", {}).get("optimize", True):
        from bengal.orchestration.css_optimizer import CSSOptimizer

        optimizer = CSSOptimizer(orchestrator.site)
        optimized_css, report = optimizer.generate(report=True)

        if optimized_css:
            # Write optimized style.css to temp location
            # AssetOrchestrator will use this instead of original
            temp_style = orchestrator.site.paths.cache_dir / "optimized-style.css"
            temp_style.write_text(optimized_css, encoding="utf-8")

            # Update asset source path
            for asset in assets_to_process:
                if asset.source_path.name == "style.css":
                    asset._optimized_source = temp_style

            cli.info(f"CSS optimized: {report['reduction_percent']}% reduction")

    # ... rest of existing phase_assets code
```

---

## Configuration

### Default Behavior (Zero Config)

```yaml
# bengal.yaml - CSS optimization is ON by default
# No configuration needed!
```

### Explicit Configuration

```yaml
# bengal.yaml
css:
  # Master switch (default: true)
  optimize: true

  # Include all color palettes (default: true)
  # Set to false for smaller bundle if you only use one palette
  all_palettes: true

  # Force-include specific CSS files (even if type not detected)
  include:
    - "components/gallery.css"  # Include even if no gallery pages

  # Force-exclude specific CSS files
  exclude:
    - "components/mermaid.css"  # Never include mermaid CSS
```

### Development Mode

```yaml
# bengal.yaml
css:
  # Disable optimization in dev for faster rebuilds
  optimize: false  # Or use CLI: bengal serve --no-css-optimize
```

---

## CLI Integration

### Build Output

```
$ bengal build

Building site...
  ✓ Content discovery (234 pages)
  ✓ CSS optimized: 52% reduction (89KB → 43KB)
    Types: blog, doc
    Features: search
  ✓ Assets processed
  ✓ Pages rendered

Build complete in 1.2s
```

### Verbose Mode

```
$ bengal build --verbose

CSS Optimization Report:
  Included: 28 files (43KB)
  Excluded: 31 files (46KB)

  Content types detected:
    ✓ blog (9 CSS files)
    ✓ doc (6 CSS files)

  Features detected:
    ✓ search (2 CSS files)

  Excluded type CSS:
    ✗ autodoc-python (not used)
    ✗ tutorial (not used)
    ✗ wiki (not used)
    ✗ recipe (not used)
```

---

## Size Estimates

### Before (Current)

| CSS Category | Files | Size (minified) |
|--------------|-------|-----------------|
| Core | 16 | ~24KB |
| Shared | 15 | ~20KB |
| Type-specific | 35+ | ~80KB |
| Features | 8 | ~16KB |
| **Total** | **74+** | **~140KB** |

### After (Optimized)

| Site Type | Included | Size | Savings |
|-----------|----------|------|---------|
| Blog only | Core + Shared + blog | ~65KB | **54%** |
| Docs only | Core + Shared + doc | ~60KB | **57%** |
| Blog + Docs | Core + Shared + blog + doc | ~85KB | **39%** |
| Recipe only | Core + Shared + recipe | ~55KB | **61%** |
| Full site (all types) | Everything | ~140KB | 0% |

---

## Testing

### Unit Tests

```python
# tests/unit/test_css_optimizer.py

def test_detects_blog_type():
    """Should detect blog content type from pages."""
    site = create_test_site(pages=[
        Page(metadata={"type": "blog"}),
    ])
    optimizer = CSSOptimizer(site)

    assert "blog" in optimizer.get_used_content_types()


def test_detects_mermaid_feature():
    """Should detect mermaid feature from content."""
    site = create_test_site(pages=[
        Page(content="```mermaid\ngraph TD\n```"),
    ])
    optimizer = CSSOptimizer(site)

    assert "mermaid" in optimizer.get_enabled_features()


def test_generates_minimal_css():
    """Should generate CSS with only needed imports."""
    site = create_test_site(pages=[
        Page(metadata={"type": "blog"}),
    ])
    optimizer = CSSOptimizer(site)
    css = optimizer.generate()

    assert "components/blog.css" in css
    assert "components/autodoc.css" not in css
    assert "components/wiki.css" not in css


def test_force_include():
    """Should include force-included CSS even if type not used."""
    site = create_test_site(
        config={"css": {"include": ["components/gallery.css"]}},
        pages=[Page(metadata={"type": "blog"})],
    )
    optimizer = CSSOptimizer(site)
    css = optimizer.generate()

    assert "components/gallery.css" in css
```

### Integration Tests

```python
# tests/integration/test_css_optimization.py

def test_optimized_build_produces_smaller_css(test_site_blog):
    """Blog-only site should have smaller CSS than full theme."""
    # Build with optimization
    build(test_site_blog, css_optimize=True)
    optimized_size = (test_site_blog.output_dir / "assets/style.css").stat().st_size

    # Build without optimization
    build(test_site_blog, css_optimize=False)
    full_size = (test_site_blog.output_dir / "assets/style.css").stat().st_size

    # Should be at least 40% smaller
    assert optimized_size < full_size * 0.6
```

---

## Migration

### For Users

**No action required.** CSS optimization is enabled by default and works automatically.

To disable:
```yaml
# bengal.yaml
css:
  optimize: false
```

### For Theme Developers

1. Create `css_manifest.py` in your theme
2. Categorize CSS files into CORE, SHARED, TYPE_MAP, FEATURE_MAP
3. Test with different site configurations

---

## Rollout Plan

### Phase 1: Core Implementation (4-6 hours)
- [ ] Create `css_manifest.py` for default theme
- [ ] Implement `CSSOptimizer` class
- [ ] Add integration point in asset phase
- [ ] Unit tests

### Phase 2: Polish (2-3 hours)
- [ ] CLI output improvements
- [ ] Configuration options
- [ ] Documentation

### Phase 3: Validation (2-3 hours)
- [ ] Integration tests
- [ ] Performance benchmarks
- [ ] Real-world site testing

**Total Effort**: 8-12 hours

---

## Open Questions

1. **Should we cache the optimization result?**
   - Pro: Faster incremental builds
   - Con: Need cache invalidation when pages change types

2. **Should themes be required to have css_manifest.py?**
   - Current: Falls back to no optimization if missing
   - Alternative: Generate manifest automatically from directory structure

3. **Should we support per-page CSS loading?**
   - More optimal but adds HTTP requests
   - Could be a future enhancement

---

## Success Criteria

- [ ] Blog-only sites see 50%+ CSS reduction
- [ ] Docs-only sites see 50%+ CSS reduction
- [ ] Mixed sites (blog + docs) see 30%+ reduction
- [ ] Full sites (all types) see no regression
- [ ] Build time impact < 50ms
- [ ] Zero external dependencies

---

## Related

- `rfc-specialized-site-types.md` - Adds new content types that need CSS
- `rfc-theme-developer-ergonomics.md` - Theme development improvements
- `architecture/asset-pipeline.md` - Asset processing details

---

## Changelog

- 2025-12-23: Initial draft
