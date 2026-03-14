"""
Asset dataclass for static file representation.

Provides the Asset class representing a static file (image, CSS, JS, font)
with methods for processing, optimization, fingerprinting, and output writing.

Public API:
Asset: Static file with processing capabilities

Key Methods:
    minify(): Minify CSS/JS content (removes whitespace, comments)
    bundle_css(): Resolve @import statements into single file
    optimize(): Optimize images (requires Pillow)
    hash(): Generate SHA256 fingerprint for cache-busting
    copy_to_output(): Write processed asset to output directory

Asset Types:
    css: Stylesheets (supports bundling, minification, nesting transform)
    javascript: Scripts (supports minification via jsmin)
    image: Images (supports optimization via Pillow)
    font: Web fonts (woff, woff2, ttf, eot)
    video: Video files (mp4, webm)
    document: Documents (pdf)
    other: Unknown file types

Processing Pipeline:
1. Create Asset(source_path=path)
2. For CSS: bundle_css() to resolve @imports
3. minify() to reduce size
4. hash() to generate fingerprint
5. copy_to_output() to write with fingerprinted filename

Related Modules:
bengal.core.asset.css_transforms: CSS nesting and minification
bengal.orchestration.asset: Asset discovery and build coordination
bengal.assets.manifest: Asset manifest for fingerprint tracking

"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bengal.services.asset_io import (
    bundle_css as asset_io_bundle_css,
)
from bengal.services.asset_io import (
    copy_asset_to_output as asset_io_copy_to_output,
)
from bengal.services.asset_io import (
    hash_content_from_source,
)
from bengal.services.asset_io import (
    minify_css as asset_io_minify_css,
)
from bengal.services.asset_io import (
    minify_js as asset_io_minify_js,
)
from bengal.services.asset_io import (
    optimize_image as asset_io_optimize_image,
)


@dataclass
class Asset:
    """
    Represents a static asset file (image, CSS, JS, etc.).

    Attributes:
        source_path: Path to the source asset file
        output_path: Path where the asset will be copied
        asset_type: Type of asset (css, js, image, font, etc.)
        fingerprint: Hash-based fingerprint for cache busting
        minified: Whether the asset has been minified
        optimized: Whether the asset has been optimized
        bundled: Whether CSS @import statements have been inlined

    """

    source_path: Path
    output_path: Path | None = None
    asset_type: str | None = None
    fingerprint: str | None = None
    minified: bool = False
    optimized: bool = False
    bundled: bool = False
    logical_path: Path | None = None

    # Processing state (set during asset processing)
    _bundled_content: str | None = None  # CSS content after @import resolution
    _minified_content: str | None = None  # Content after minification
    _optimized_image: Any = None  # Optimized PIL Image (type deferred to avoid PIL import)
    _site: Any | None = field(default=None, repr=False)
    _diagnostics: Any | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Determine asset type from file extension."""
        if not self.asset_type:
            self.asset_type = self._determine_type()
        if self.logical_path is None:
            if self.output_path is not None:
                self.logical_path = Path(self.output_path)
            else:
                self.logical_path = Path(self.source_path.name)

    def _determine_type(self) -> str:
        """
        Determine the asset type from the file extension.

        Returns:
            Asset type string
        """
        ext = self.source_path.suffix.lower()

        type_map = {
            ".css": "css",
            ".js": "javascript",
            ".jpg": "image",
            ".jpeg": "image",
            ".png": "image",
            ".gif": "image",
            ".svg": "image",
            ".webp": "image",
            ".woff": "font",
            ".woff2": "font",
            ".ttf": "font",
            ".eot": "font",
            ".mp4": "video",
            ".webm": "video",
            ".pdf": "document",
        }

        return type_map.get(ext, "other")

    def is_css_entry_point(self) -> bool:
        """
        Check if this asset is a CSS entry point that should be bundled.

        Entry points are CSS files named 'style.css' at any level.
        These files typically contain @import statements that pull in other CSS.

        Returns:
            True if this is a CSS entry point (e.g., style.css)
        """
        return self.asset_type == "css" and self.source_path.name == "style.css"

    def is_css_module(self) -> bool:
        """
        Check if this asset is a CSS module (imported by an entry point).

        CSS modules are CSS files that are NOT entry points.
        They should be bundled into entry points, not copied separately.

        Returns:
            True if this is a CSS module (e.g., components/buttons.css)
        """
        return self.asset_type == "css" and not self.is_css_entry_point()

    def is_js_entry_point(self) -> bool:
        """
        Check if this asset is a JS entry point for bundling.

        The JS bundle entry point is named 'bundle.js' and contains
        all theme JavaScript concatenated together.

        Returns:
            True if this is a JS bundle entry point
        """
        return self.asset_type == "javascript" and self.source_path.name == "bundle.js"

    def is_js_module(self) -> bool:
        """
        Check if this asset is a JS module (should be bundled, not copied separately).

        JS modules are individual JS files that will be bundled into bundle.js.
        They should not be copied separately when bundling is enabled.

        Excludes:
        - Third-party libraries (*.min.js) - copied separately for caching
        - The bundle entry point itself

        Returns:
            True if this is a JS module that should be bundled
        """
        if self.asset_type != "javascript":
            return False

        name = self.source_path.name

        # Not a module if it's the bundle entry point
        if name == "bundle.js":
            return False

        # Third-party minified libraries should be copied separately
        return not name.endswith(".min.js")

    def minify(self) -> Asset:
        """
        Minify the asset (for CSS and JS).

        Returns:
            Self for method chaining
        """
        if self.asset_type == "css":
            self._minify_css()
        elif self.asset_type == "javascript":
            self._minify_js()

        self.minified = True
        return self

    def bundle_css(self) -> str:
        """
        Bundle CSS by resolving all @import statements recursively.

        This creates a single CSS file from an entry point that has @imports.
        Works without any external dependencies.

        Preserves @layer blocks when bundling @import statements.

        Returns:
            Bundled CSS content as a string
        """
        bundled = asset_io_bundle_css(self.source_path, context=self)
        self.bundled = True
        return bundled

    def _minify_css(self) -> None:
        """
        Minify CSS content using simple, safe minifier.

        This minifier:
        - Removes comments and unnecessary whitespace
        - Transforms CSS nesting syntax for browser compatibility
        - Preserves all other CSS syntax (@layer, @import, etc.)

        For CSS entry points (style.css), this should be called AFTER bundling.
        """
        css_content = (
            self._bundled_content
            if self._bundled_content is not None
            else self.source_path.read_text(encoding="utf-8")
        )
        self._minified_content = asset_io_minify_css(css_content, context=self)

    def _minify_js(self) -> None:
        """Minify JavaScript content."""
        result = asset_io_minify_js(self.source_path, context=self)
        if result is not None:
            self._minified_content = result

    def hash(self) -> str:
        """
        Generate a hash-based fingerprint for the asset.

        Returns:
            Hash string (first 8 characters of SHA256)
        """
        self.fingerprint = hash_content_from_source(self)
        return self.fingerprint

    def optimize(self) -> Asset:
        """
        Optimize the asset (especially for images).

        Returns:
            Self for method chaining
        """
        if self.asset_type == "image":
            self._optimize_image()

        self.optimized = True
        return self

    def _optimize_image(self) -> None:
        """Optimize image assets."""
        self._optimized_image = asset_io_optimize_image(self.source_path, context=self)

    def copy_to_output(self, output_dir: Path, use_fingerprint: bool = True) -> Path:
        """
        Copy the asset to the output directory.

        Args:
            output_dir: Output directory path
            use_fingerprint: Whether to include fingerprint in filename

        Returns:
            Path where the asset was copied
        """
        return asset_io_copy_to_output(self, output_dir, use_fingerprint, context=self)

    @property
    def href(self) -> str:
        """
        Asset URL for templates.

        Wraps site._asset_url() logic which handles:
        - Fingerprinting (style.css -> style.1234.css)
        - Baseurl application
        - file:// protocol relative path generation

        Returns:
            Asset URL with baseurl applied
        """
        if not self._site:
            # Fallback if site not available
            logical_str = str(self.logical_path) if self.logical_path else self.source_path.name
            return f"/assets/{logical_str}"

        # Try to use template engine's _asset_url if available
        # This handles fingerprinting and manifest lookup
        try:
            # Check if site has template_engine with _asset_url
            if hasattr(self._site, "template_engine") and hasattr(
                self._site.template_engine, "_asset_url"
            ):
                logical_str = str(self.logical_path) if self.logical_path else self.source_path.name
                return self._site.template_engine._asset_url(logical_str)
        except Exception:
            pass

        # Fallback: simple baseurl application
        logical_str = str(self.logical_path) if self.logical_path else self.source_path.name
        from bengal.rendering.utils.url import apply_baseurl

        return apply_baseurl(f"/assets/{logical_str}", self._site)

    @property
    def _path(self) -> str:
        """
        Internal logical path (e.g. 'assets/css/style.css').

        Use for internal operations only:
        - Cache keys
        - Asset lookups
        - Manifest entries

        NEVER use in templates - use .href instead.
        """
        if self.logical_path:
            return str(self.logical_path)
        if self.output_path:
            return str(self.output_path)
        return self.source_path.name

    @property
    def absolute_href(self) -> str:
        """
        Fully-qualified URL for meta tags and sitemaps when available.

        If baseurl is absolute, returns href. Otherwise returns href as-is
        (root-relative) since no fully-qualified site origin is configured.
        """
        return self.href

    def __repr__(self) -> str:
        return f"Asset(type='{self.asset_type}', source='{self.source_path.name}')"
