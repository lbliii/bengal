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

import hashlib
import shutil
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bengal.assets.manifest import AssetManifest
from bengal.core.asset.css_transforms import transform_css_nesting
from bengal.core.diagnostics import emit as emit_diagnostic


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
        import re

        def bundle_imports(css_content: str, base_path: Path) -> str:
            """Recursively resolve @import statements, preserving @layer blocks."""
            from re import Match

            # Pattern for @import statements
            import_pattern = r'@import\s+(?:url\()?\s*[\'"]([^\'"]+)[\'"]\s*(?:\))?\s*;'

            def resolve_import_in_context(
                import_match: Match[str], layer_name: str | None = None
            ) -> str:
                """Resolve a single @import statement."""
                import_path = import_match.group(1)
                imported_file = base_path / import_path

                if not imported_file.exists():
                    # Keep the @import (might be a URL or external)
                    return import_match.group(0)

                try:
                    # Read and recursively process the imported file
                    imported_content = imported_file.read_text(encoding="utf-8")
                    # Recursively resolve nested imports
                    bundled_content = bundle_imports(imported_content, imported_file.parent)

                    # Return bundled content so it can replace the @layer block body
                    return bundled_content
                except (OSError, PermissionError) as e:
                    emit_diagnostic(
                        self,
                        "warning",
                        "css_import_read_failed",
                        imported_file=str(imported_file),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return import_match.group(0)
                except Exception as e:
                    emit_diagnostic(
                        self,
                        "error",
                        "css_import_unexpected_error",
                        imported_file=str(imported_file),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return import_match.group(0)

            def find_layer_block_end(css: str, start_pos: int) -> int:
                """
                Find the end position of a @layer block using brace counting.
                Handles nested braces correctly (e.g., media queries, nested rules).

                Args:
                    css: CSS content string
                    start_pos: Position after the opening brace of @layer block

                Returns:
                    Position of the matching closing brace, or -1 if not found
                """
                brace_count = 1  # We start after the opening brace
                i = start_pos
                in_string = False
                string_char = None

                while i < len(css) and brace_count > 0:
                    char = css[i]

                    # Handle string literals (skip braces inside strings)
                    if not in_string and char in ("'", '"'):
                        in_string = True
                        string_char = char
                    elif in_string:
                        if char == "\\" and i + 1 < len(css):
                            i += 2  # Skip escaped character
                            continue
                        elif char == string_char:
                            in_string = False
                            string_char = None

                    # Count braces (only when not in string)
                    if not in_string:
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1

                    i += 1

                # Return position of closing brace (i-1 because we incremented after finding it)
                return i - 1 if brace_count == 0 else -1

            def process_layer_blocks(css: str) -> str:
                """
                Process @layer blocks, replacing @import statements inside them.
                Uses brace counting to handle nested braces correctly.
                """
                result = []
                i = 0

                while i < len(css):
                    # Look for @layer declaration
                    layer_match = re.search(r"@layer\s+\w+\s*\{", css[i:])
                    if not layer_match:
                        # No more @layer blocks, append rest of content
                        result.append(css[i:])
                        break

                    # Append content before @layer block
                    layer_start = i + layer_match.start()
                    result.append(css[i:layer_start])

                    # Find the opening brace position
                    brace_pos = layer_start + layer_match.end() - 1  # Position of '{'
                    layer_decl = css[layer_start : brace_pos + 1]  # "@layer name {"

                    # Extract layer name
                    layer_name_match = re.match(r"@layer\s+(\w+)", layer_decl)
                    layer_name: str = layer_name_match.group(1) if layer_name_match else ""

                    # Find the matching closing brace using brace counting
                    content_start = brace_pos + 1
                    content_end = find_layer_block_end(css, content_start)

                    if content_end == -1:
                        # Malformed @layer block, keep as-is
                        result.append(css[layer_start:])
                        break

                    # Extract content inside @layer block
                    layer_content = css[content_start:content_end]

                    # Process @import statements inside this layer
                    current_layer = layer_name  # Capture for closure

                    def layer_resolver(m: re.Match[str], layer: str = current_layer) -> str:
                        return resolve_import_in_context(m, layer)

                    processed_content = re.sub(
                        import_pattern,
                        layer_resolver,
                        layer_content,
                    )

                    # Reconstruct @layer block
                    result.append(layer_decl)
                    result.append(processed_content)
                    result.append("}")

                    # Continue after this @layer block
                    i = content_end + 1

                return "".join(result)

            # Process @layer blocks first (using brace counting)
            result = process_layer_blocks(css_content)

            # Then process standalone @import statements (not in @layer)
            result = re.sub(import_pattern, lambda m: resolve_import_in_context(m), result)

            return result

        # Read the CSS file
        with open(self.source_path, encoding="utf-8") as f:
            css_content = f.read()

        # Bundle all @import statements
        bundled = bundle_imports(css_content, self.source_path.parent)
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
        # Get the CSS content (bundled if this is an entry point, otherwise read from file)
        if self._bundled_content is not None:
            css_content = self._bundled_content
        else:
            with open(self.source_path, encoding="utf-8") as f:
                css_content = f.read()

        try:
            # Transform CSS nesting first (for browser compatibility)
            css_content = transform_css_nesting(css_content)

            from bengal.utils.css_minifier import minify_css

            # Simple minification: remove comments and whitespace only
            # No transformations that could break CSS
            self._minified_content = minify_css(css_content)
        except Exception as e:
            emit_diagnostic(
                self,
                "error",
                "css_minification_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # On error, use original content (fail-safe)
            self._minified_content = css_content

    def _minify_js(self) -> None:
        """Minify JavaScript content."""
        # If a file is already explicitly minified (common for third-party libs),
        # do not re-minify. This avoids expensive `jsmin()` work and prevents
        # unnecessary content churn.
        if self.source_path.name.endswith(".min.js"):
            return
        try:
            from jsmin import jsmin

            with open(self.source_path, encoding="utf-8") as f:
                js_content = f.read()

            minified_content = jsmin(js_content)
            self._minified_content = minified_content
        except ImportError:
            emit_diagnostic(self, "warning", "jsmin_unavailable", source=str(self.source_path))

    def _hash_source_chunks(self) -> Iterator[bytes]:
        """
        Yield byte chunks representing the content that should drive fingerprinting.

        Prefers minified (or bundled) content so hashes match the bytes we actually emit.
        Falls back to the original file contents when no in-memory transform exists.
        """
        if self._minified_content is not None:
            yield self._minified_content.encode("utf-8")
            return

        if self._bundled_content is not None:
            yield self._bundled_content.encode("utf-8")
            return

        with open(self.source_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    def hash(self) -> str:
        """
        Generate a hash-based fingerprint for the asset.

        Returns:
            Hash string (first 8 characters of SHA256)
        """
        # Performance: stream the hash computation to avoid allocating the entire
        # asset bytes in memory (many assets, some large).
        hasher = hashlib.sha256()
        for chunk in self._hash_source_chunks():
            hasher.update(chunk)
        self.fingerprint = hasher.hexdigest()[:8]
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
        if self.source_path.suffix.lower() == ".svg":
            # Skip SVG optimization - vector format, no raster compression needed
            emit_diagnostic(self, "debug", "svg_optimization_skipped", source=str(self.source_path))
            self.optimized = True
            return

        try:
            from PIL import Image
            from PIL.Image import Image as PILImage

            img: PILImage = Image.open(self.source_path)

            # Basic optimization - could be expanded
            if img.mode in ("RGBA", "LA"):
                # Keep alpha channel
                pass
            else:
                # Convert to RGB if needed
                img = img.convert("RGB")

            # Store optimized image (would be saved during copy_to_output)
            self._optimized_image = img
        except ImportError:
            emit_diagnostic(self, "warning", "pillow_unavailable", source=str(self.source_path))
        except Exception as e:
            emit_diagnostic(
                self,
                "warning",
                "image_optimization_failed",
                source=str(self.source_path),
                error=str(e),
                error_type=type(e).__name__,
            )

    def copy_to_output(self, output_dir: Path, use_fingerprint: bool = True) -> Path:
        """
        Copy the asset to the output directory.

        Args:
            output_dir: Output directory path
            use_fingerprint: Whether to include fingerprint in filename

        Returns:
            Path where the asset was copied
        """
        # Only generate fingerprint if explicitly requested
        if use_fingerprint:
            if not self.fingerprint:
                self.hash()
            # Clean up old fingerprints after generating new one, before writing
            self._cleanup_old_fingerprints_prepare(output_dir)

        # Determine output filename
        if use_fingerprint and self.fingerprint:
            out_name = f"{self.source_path.stem}.{self.fingerprint}{self.source_path.suffix}"
        else:
            out_name = self.source_path.name

        # Determine output path maintaining directory structure
        if self.output_path:
            # Insert fingerprint into filename while preserving directory structure
            parent = (output_dir / self.output_path).parent
            output_path = parent / out_name
        else:
            output_path = output_dir / out_name

        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy or write optimized/minified content atomically
        if self._minified_content is not None:
            # Write minified content atomically (crash-safe)
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(
                output_path,
                self._minified_content,
                encoding="utf-8",
                ensure_parent=False,  # parent dir already ensured above
            )
        elif self._optimized_image is not None:
            # Save optimized image atomically using unique temp file to prevent race conditions
            import os
            import threading
            import uuid

            pid = os.getpid()
            tid = threading.get_ident()
            unique_id = uuid.uuid4().hex[:8]
            tmp_path = output_path.parent / f".{output_path.name}.{pid}.{tid}.{unique_id}.tmp"
            try:
                # Determine image format from original file extension (not .tmp)
                img_format = None
                ext = output_path.suffix.upper().lstrip(".")
                if ext in ("JPG", "JPEG"):
                    img_format = "JPEG"
                elif ext in ("PNG", "GIF", "WEBP"):
                    img_format = ext

                self._optimized_image.save(tmp_path, format=img_format, optimize=True, quality=85)
                tmp_path.replace(output_path)
            except Exception as e:
                emit_diagnostic(
                    self,
                    "error",
                    "atomic_image_save_failed",
                    path=str(output_path),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                tmp_path.unlink(missing_ok=True)
                raise
        else:
            # Simple copy (shutil.copy2 is already safe for most cases)
            shutil.copy2(self.source_path, output_path)

        self.output_path = output_path
        return output_path

    def _cleanup_old_fingerprints_prepare(self, output_dir: Path) -> None:
        """
        Remove outdated fingerprinted siblings before writing the new file.

        This ensures only one fingerprinted version exists at a time, preventing
        stale files from being served.

        Args:
            output_dir: Output directory where assets are written
        """
        try:
            site = getattr(self, "_site", None)
            if site is not None and bool(getattr(site, "config", {}).get("_clean_output_this_run")):
                # Clean output implies no stale fingerprints can exist.
                return

            # Determine where the file will be written
            parent = (output_dir / self.output_path).parent if self.output_path else output_dir

            if not parent.exists():
                return  # Directory doesn't exist yet, nothing to clean

            # Track if we successfully cleaned up via manifest lookup
            manifest_cleanup_done = False

            # Performance: if we have the previous manifest loaded, delete the exact
            # stale fingerprinted output path (if any) instead of scanning directories.
            if site is not None:
                try:
                    prev: AssetManifest | None = getattr(site, "_asset_manifest_previous", None)
                    if prev is not None and self.logical_path is not None:
                        logical_str = self.logical_path.as_posix()
                        prev_entry = prev.get(logical_str)
                        if prev_entry is not None and prev_entry.output_path:
                            old_full = Path(site.output_dir) / Path(prev_entry.output_path)
                            if (
                                old_full.exists()
                                and self.fingerprint is not None
                                and not old_full.name.endswith(
                                    f".{self.fingerprint}{self.source_path.suffix}"
                                )
                            ):
                                old_full.unlink(missing_ok=True)
                                manifest_cleanup_done = True
                except Exception:
                    # Best-effort only; fall back to directory scan.
                    pass

            # If manifest cleanup was successful, we're done
            if manifest_cleanup_done:
                return

            # Find all existing fingerprinted versions of this asset (fallback/safety)
            pattern = f"{self.source_path.stem}.*{self.source_path.suffix}"
            for candidate in parent.glob(pattern):
                # Skip if this is the file we're about to write (fingerprint already generated)
                if self.fingerprint and candidate.name.endswith(
                    f".{self.fingerprint}{self.source_path.suffix}"
                ):
                    continue
                # Remove stale fingerprints (not the current one).
                # This prevents serving older fingerprinted assets after an update.
                candidate.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            emit_diagnostic(
                self,
                "debug",
                "asset_fingerprint_cleanup_failed",
                asset=str(self.source_path),
                error=str(exc),
            )

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
        from bengal.rendering.template_engine.url_helpers import with_baseurl

        return with_baseurl(f"/assets/{logical_str}", self._site)

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
