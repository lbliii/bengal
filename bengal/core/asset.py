"""
Asset Object - Handles images, CSS, JS, and other static files.
"""

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Module-level flag to track if we've warned about missing lightningcss
_warned_no_bundling = False


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

    def __post_init__(self) -> None:
        """Determine asset type from file extension."""
        if not self.asset_type:
            self.asset_type = self._determine_type()

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

    def minify(self) -> "Asset":
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

        Returns:
            Bundled CSS content as a string
        """
        import re

        def bundle_imports(css_content: str, base_path: Path) -> str:
            """Recursively resolve @import statements."""
            # Pattern: @import url('...') or @import '...'
            import_pattern = r'@import\s+(?:url\()?\s*[\'"]([^\'"]+)[\'"]\s*(?:\))?\s*;'

            def resolve_import(match):
                import_path = match.group(1)
                imported_file = base_path / import_path

                if not imported_file.exists():
                    # Keep the @import (might be a URL or external)
                    return match.group(0)

                try:
                    # Read and recursively process the imported file
                    imported_content = imported_file.read_text(encoding="utf-8")
                    # Recursively resolve nested imports
                    return bundle_imports(imported_content, imported_file.parent)
                except Exception as e:
                    logger.warning(
                        "css_import_read_failed",
                        imported_file=str(imported_file),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return match.group(0)

            # Replace all @import statements with their content
            return re.sub(import_pattern, resolve_import, css_content)

        # Read the CSS file
        with open(self.source_path, encoding="utf-8") as f:
            css_content = f.read()

        # Bundle all @import statements
        bundled = bundle_imports(css_content, self.source_path.parent)
        self.bundled = True

        return bundled

    def _minify_css(self) -> None:
        """
        Minify CSS content using lightningcss (preferred) or csscompressor (fallback).

        For CSS entry points (style.css), this should be called AFTER bundling.
        """
        # Get the CSS content (bundled if this is an entry point)
        if hasattr(self, "_bundled_content"):
            css_content = self._bundled_content
        else:
            with open(self.source_path, encoding="utf-8") as f:
                css_content = f.read()

        # Try Lightning CSS for minification + autoprefixing
        try:
            import lightningcss

            result = lightningcss.process_stylesheet(
                css_content,
                filename=str(self.source_path),
                minify=True,
                # Autoprefix for modern browsers
                browsers_list=[
                    "last 2 Chrome versions",
                    "last 2 Firefox versions",
                    "last 2 Safari versions",
                    "last 2 Edge versions",
                ],
            )

            self._minified_content = result

        except ImportError:
            # Fallback: try csscompressor (basic minification only)
            try:
                import csscompressor

                minified_content = csscompressor.compress(css_content)
                self._minified_content = minified_content

                # Warn about missing lightningcss (only once per build)
                global _warned_no_bundling
                if not _warned_no_bundling:
                    logger.warning(
                        "lightningcss_unavailable",
                        info="CSS will be minified but not autoprefixed",
                        install_command="pip install lightningcss",
                    )
                    _warned_no_bundling = True

            except ImportError:
                # No minification available - just use the content as-is
                logger.warning("no_css_minifier_available")
                self._minified_content = css_content

        except Exception as e:
            # If Lightning CSS fails, fall back to csscompressor
            logger.warning(
                "lightningcss_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                fallback="csscompressor",
            )
            try:
                import csscompressor

                self._minified_content = csscompressor.compress(css_content)
            except Exception as fallback_error:
                logger.error(
                    "css_fallback_minification_failed",
                    error=str(fallback_error),
                    error_type=type(fallback_error).__name__,
                )
                self._minified_content = css_content

    def _minify_js(self) -> None:
        """Minify JavaScript content."""
        try:
            from jsmin import jsmin

            with open(self.source_path, encoding="utf-8") as f:
                js_content = f.read()

            minified_content = jsmin(js_content)
            self._minified_content = minified_content
        except ImportError:
            logger.warning("jsmin_unavailable", source=str(self.source_path))

    def hash(self) -> str:
        """
        Generate a hash-based fingerprint for the asset.

        Returns:
            Hash string (first 8 characters of SHA256)
        """
        hasher = hashlib.sha256()

        with open(self.source_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)

        self.fingerprint = hasher.hexdigest()[:8]
        return self.fingerprint

    def optimize(self) -> "Asset":
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
        try:
            from PIL import Image

            img = Image.open(self.source_path)

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
            logger.warning("pillow_unavailable", source=str(self.source_path))
        except Exception as e:
            logger.warning(
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
        # Generate fingerprint if requested and not already done
        if use_fingerprint and not self.fingerprint:
            # Prefer hashing minified content when available to keep URLs stable with output
            if hasattr(self, "_minified_content") and isinstance(self._minified_content, str):
                import hashlib as _hashlib

                hasher = _hashlib.sha256()
                hasher.update(self._minified_content.encode("utf-8"))
                self.fingerprint = hasher.hexdigest()[:8]
            else:
                self.hash()

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
        if hasattr(self, "_minified_content"):
            # Write minified content atomically (crash-safe)
            from bengal.utils.atomic_write import atomic_write_text

            atomic_write_text(output_path, self._minified_content, encoding="utf-8")
        elif hasattr(self, "_optimized_image"):
            # Save optimized image atomically
            tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
            try:
                self._optimized_image.save(tmp_path, optimize=True, quality=85)
                tmp_path.replace(output_path)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
        else:
            # Simple copy (shutil.copy2 is already safe for most cases)
            shutil.copy2(self.source_path, output_path)

        self.output_path = output_path
        return output_path

    def __repr__(self) -> str:
        return f"Asset(type='{self.asset_type}', source='{self.source_path.name}')"
