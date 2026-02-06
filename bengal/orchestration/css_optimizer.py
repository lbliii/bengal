"""
Content-aware CSS tree shaking.

Analyzes site content to determine which CSS files are needed,
then generates an optimized style.css with only necessary imports.
This can reduce CSS bundle size by 50%+ for single-purpose sites.

Key Features:
- Zero external dependencies (pure Python)
- Automatic detection of content types and features
- Preserves CSS @layer structure for proper cascade
- Graceful fallback if no manifest available
- Full reporting for build output

Usage:
from bengal.orchestration.css_optimizer import CSSOptimizer

    optimizer = CSSOptimizer(site)
optimized_css, report = optimizer.generate(report=True)

# Or use convenience function
from bengal.orchestration.css_optimizer import optimize_css_for_site
    css = optimize_css_for_site(site)

See Also:
- bengal/themes/default/css_manifest.py: Default theme manifest
- plan/drafted/rfc-css-tree-shaking.md: Design rationale

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.orchestration.css_manifest_types import CSSManifest, CSSOptimizationReport
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

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
        _manifest: Loaded CSS manifest from theme

    Example:
        optimizer = CSSOptimizer(site)
        optimized_css = optimizer.generate()

        # Or with reporting
        optimized_css, report = optimizer.generate(report=True)
        print(f"Included {report['included_count']} of {report['total_count']} CSS files")

    """

    def __init__(self, site: Site) -> None:
        """
        Initialize CSS optimizer.

        Args:
            site: Site instance to analyze for content types and features
        """
        self.site = site
        self._manifest: CSSManifest = self._load_manifest()

    def _load_manifest(self) -> CSSManifest:
        """
        Load CSS manifest from theme.

        Attempts to load the CSS manifest from the active theme.
        Falls back to empty manifest if theme doesn't have one.

        Returns:
            CSSManifest dictionary with categorized CSS files
        """
        # Try to load from the active theme
        theme_name = self.site.theme or "default"

        try:
            # First check for default theme (bundled with Bengal)
            if theme_name == "default":
                from bengal.themes.default.css_manifest import (
                    CSS_CORE,
                    CSS_EXPERIMENTAL,
                    CSS_FEATURE_MAP,
                    CSS_PALETTES,
                    CSS_SHARED,
                    CSS_TYPE_MAP,
                    MANIFEST_VERSION,
                )

                return CSSManifest(
                    core=CSS_CORE,
                    shared=CSS_SHARED,
                    type_map=CSS_TYPE_MAP,
                    feature_map=CSS_FEATURE_MAP,
                    palettes=CSS_PALETTES,
                    experimental=CSS_EXPERIMENTAL,
                    version=MANIFEST_VERSION,
                )

            # For custom themes, check for css_manifest.py in theme directory
            theme_dir = self._get_theme_dir(theme_name)
            if theme_dir:
                manifest_path = theme_dir / "css_manifest.py"
                if manifest_path.exists():
                    return self._load_manifest_from_path(manifest_path)

            logger.debug(
                "css_manifest_not_found",
                theme=theme_name,
                details="Falling back to no optimization",
            )
            return CSSManifest()

        except ImportError as e:
            logger.warning(
                "css_manifest_import_failed",
                theme=theme_name,
                error=str(e),
            )
            return CSSManifest()

    def _get_theme_dir(self, theme_name: str) -> Any:
        """Get the directory path for a theme."""
        from pathlib import Path

        import bengal

        # Check in site's themes directory
        site_theme_dir = self.site.root_path / "themes" / theme_name
        if site_theme_dir.exists():
            return site_theme_dir

        # Check in Bengal's bundled themes
        assert bengal.__file__ is not None, "bengal module has no __file__"
        bengal_dir = Path(bengal.__file__).parent
        bundled_theme_dir = bengal_dir / "themes" / theme_name
        if bundled_theme_dir.exists():
            return bundled_theme_dir

        return None

    def _load_manifest_from_path(self, manifest_path: Any) -> CSSManifest:
        """Load manifest from a Python file path."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("css_manifest", manifest_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return CSSManifest(
                core=getattr(module, "CSS_CORE", []),
                shared=getattr(module, "CSS_SHARED", []),
                type_map=getattr(module, "CSS_TYPE_MAP", {}),
                feature_map=getattr(module, "CSS_FEATURE_MAP", {}),
                palettes=getattr(module, "CSS_PALETTES", []),
                experimental=getattr(module, "CSS_EXPERIMENTAL", []),
                version=getattr(module, "MANIFEST_VERSION", 1),
            )

        return CSSManifest()

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
            # Check page type from metadata
            page_type = page.metadata.get("type")
            if page_type:
                types.add(page_type)

            # Also check content_type if present
            content_type = page.metadata.get("content_type")
            if content_type:
                types.add(content_type)

        for section in self.site.sections:
            # Check section content_type from metadata
            ct = section.metadata.get("content_type")
            if ct:
                types.add(ct)

            # Also check type if present
            section_type = section.metadata.get("type")
            if section_type:
                types.add(section_type)

        logger.debug("css_types_detected", types=sorted(types))
        return types

    def get_enabled_features(self) -> set[str]:
        """
        Detect features that require CSS.

        Checks:
        - site.features_detected (populated during discovery phase)
        - site.config.features (explicit overrides)

        Returns:
            Set of feature names (e.g., {"search", "graph"})
        """
        features: set[str] = set()

        # 1. Start with auto-detected features from discovery
        # Prefer BuildState (fresh each build), fall back to Site field
        _bs = getattr(self.site, "build_state", None)
        if _bs is not None:
            features.update(_bs.features_detected)
        elif hasattr(self.site, "features_detected"):
            features.update(self.site.features_detected)

        # 2. Add explicit config overrides
        feature_config = self.site.config.get("features", {})
        if isinstance(feature_config, dict):
            for feature, enabled in feature_config.items():
                if enabled:
                    features.add(feature)
                elif enabled is False:
                    # Explicitly disabled in config
                    features.discard(feature)

        # 3. Check for search if enabled in config
        if self.site.config.get("search", {}).get("enabled", False):
            features.add("search")

        # 4. Check for graph if enabled in config
        if self.site.config.get("graph", {}).get("enabled", False):
            features.add("graph")

        logger.debug("css_features_detected", features=sorted(features))
        return features

    def get_required_css_files(self) -> list[str]:
        """
        Determine which CSS files are needed.

        Combines:
        - Core CSS (always)
        - Palettes (all or just active based on config)
        - Shared CSS (always)
        - Type-specific CSS (based on content types)
        - Feature-specific CSS (based on features)
        - Force-include from config

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
        css_cfg = self.site.config.get("css", {})
        if not isinstance(css_cfg, dict):
            css_cfg = {}
        include_all_palettes = css_cfg.get("all_palettes", True)

        if include_all_palettes:
            imports.extend(palettes)
        else:
            # Only active palette
            theme_cfg = self.site.config.get("theme", {})
            if isinstance(theme_cfg, dict):
                active = theme_cfg.get("palette", "blue-bengal")
            else:
                active = "blue-bengal"
            matching = [p for p in palettes if active in p]
            imports.extend(matching or palettes[:1])  # Fallback to first

        # 3. Shared - common components
        imports.extend(self._manifest.get("shared", []))

        # 4. Get include/exclude config (supports both content types and file paths)
        force_include = css_cfg.get("include", [])
        force_exclude = css_cfg.get("exclude", [])
        if not isinstance(force_include, list):
            force_include = []
        if not isinstance(force_exclude, list):
            force_exclude = []

        type_map = self._manifest.get("type_map", {})
        feature_map = self._manifest.get("feature_map", {})

        # Resolve force_include: content types/features add their CSS files
        additional_files: list[str] = []
        for item in force_include:
            if item in type_map:
                additional_files.extend(type_map[item])
            elif item in feature_map:
                additional_files.extend(feature_map[item])
            elif item.endswith(".css"):
                # Raw file path
                additional_files.append(item)

        # Resolve force_exclude: content types/features to skip
        excluded_types: set[str] = set()
        excluded_features: set[str] = set()
        excluded_files: set[str] = set()
        for item in force_exclude:
            if item in type_map:
                excluded_types.add(item)
            elif item in feature_map:
                excluded_features.add(item)
            elif item.endswith(".css"):
                excluded_files.add(item)

        # 5. Type-specific (minus excluded types)
        used_types = self.get_used_content_types()

        for content_type in used_types:
            if content_type not in excluded_types:
                css_files = type_map.get(content_type)
                if css_files:
                    imports.extend(css_files)

        # 6. Feature-specific (minus excluded features)
        enabled_features = self.get_enabled_features()

        for feature in enabled_features:
            if feature not in excluded_features:
                css_files = feature_map.get(feature)
                if css_files:
                    imports.extend(css_files)

        # 7. Add force-included files
        imports.extend(additional_files)

        # Deduplicate while preserving order and filtering file-level exclusions
        seen: set[str] = set()
        unique: list[str] = []
        for css_file in imports:
            if css_file not in seen and css_file not in excluded_files:
                seen.add(css_file)
                unique.append(css_file)

        return unique

    def generate(self, report: bool = False) -> str | tuple[str, CSSOptimizationReport]:
        """
        Generate optimized style.css content.

        Creates a CSS file with @layer imports containing only the CSS
        files needed for the detected content types and features.

        Args:
            report: If True, also return optimization report

        Returns:
            CSS content string, or tuple of (css_content, report_dict) if report=True
        """
        imports = self.get_required_css_files()

        if not imports:
            # No manifest or empty = return empty (use original style.css)
            logger.info("css_optimization_skipped", reason="no_manifest")
            if report:
                return "", CSSOptimizationReport(
                    skipped=True,
                    included_count=0,
                    excluded_count=0,
                    total_count=0,
                    reduction_percent=0,
                    types_detected=[],
                    features_detected=[],
                    included_files=[],
                    excluded_files=[],
                )
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
            "experimental/": "components",
        }

        # Generate CSS with @layer blocks
        lines = [
            "/* Bengal SSG - Optimized CSS Bundle */",
            "/* Auto-generated based on content types detected */",
            "",
            "@layer tokens, base, utilities, components, pages;",
            "",
        ]

        for css_file in imports:
            # Determine layer based on file path prefix
            layer = "components"  # default
            for prefix, layer_name in layer_map.items():
                if css_file.startswith(prefix):
                    layer = layer_name
                    break

            # Handle third-party libraries (no prefix)
            if not any(css_file.startswith(p) for p in layer_map) and css_file.endswith(".min.css"):
                layer = "components"

            lines.append(f"@layer {layer} {{ @import url('{css_file}'); }}")

        css_content = "\n".join(lines)

        # Build report if requested
        if report:
            all_files = self._get_all_css_files()
            excluded = set(all_files) - set(imports)

            report_data = CSSOptimizationReport(
                skipped=False,
                included_count=len(imports),
                excluded_count=len(excluded),
                total_count=len(all_files),
                reduction_percent=round(len(excluded) / max(len(all_files), 1) * 100),
                types_detected=sorted(self.get_used_content_types()),
                features_detected=sorted(self.get_enabled_features()),
                included_files=imports,
                excluded_files=sorted(excluded),
            )

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
    result = optimizer.generate()
    if isinstance(result, tuple):
        return result[0]
    return result
