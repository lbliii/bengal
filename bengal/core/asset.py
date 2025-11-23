"""
Asset Object - Handles images, CSS, JS, and other static files.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Module-level flag to track if we've warned about missing lightningcss
_warned_no_bundling = False


def _transform_css_nesting(css: str) -> str:
    """
    Transform CSS nesting syntax (&:hover, &.class, etc.) to traditional selectors.

    Transforms patterns like:
        .parent {
          color: red;
          &:hover { color: blue; }
        }
    Into:
        .parent { color: red; }
        .parent:hover { color: blue; }

    This ensures compatibility when lightningcss is unavailable.
    
    NOTE: We should NOT write nested CSS in source files. Use traditional selectors instead.
    This is a safety net for any nested CSS that slips through.
    """
    import re

    result = css
    
    # Pattern to match CSS rule blocks
    rule_pattern = r'([^{]+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    
    def transform_rule(match):
        selector = match.group(1).strip()
        block_content = match.group(2)
        
        # Skip @rules
        if selector.strip().startswith('@'):
            return match.group(0)
        
        # Clean @layer prefixes
        selector_clean = re.sub(r'^@layer\s+\w+\s*', '', selector).strip()
        has_layer = selector.strip().startswith('@layer')
        layer_decl = ''
        if has_layer:
            layer_match = re.match(r'(@layer\s+\w+)\s*', selector)
            if layer_match:
                layer_decl = layer_match.group(1) + ' '
        
        if not selector_clean or selector_clean.startswith('@'):
            return match.group(0)
        
        # Find nested & selectors
        nested_pattern = r'&\s*([:.#\[\w\s-]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        nested_rules = []
        
        def extract_nested(m):
            nested_selector_part = m.group(1).strip()
            nested_block = m.group(2)
            
            # Build full selector
            if nested_selector_part.startswith(':'):
                full_selector = selector_clean + nested_selector_part
            elif nested_selector_part.startswith('.'):
                full_selector = selector_clean + nested_selector_part
            elif nested_selector_part.startswith('['):
                full_selector = selector_clean + nested_selector_part
            elif nested_selector_part.startswith(' '):
                full_selector = selector_clean + nested_selector_part
            else:
                full_selector = selector_clean + nested_selector_part
            
            if has_layer:
                nested_rules.append(f"{layer_decl}{full_selector} {{{nested_block}}}")
            else:
                nested_rules.append(f"{full_selector} {{{nested_block}}}")
            return ""
        
        remaining_content = re.sub(nested_pattern, extract_nested, block_content, flags=re.MULTILINE)
        remaining_content = re.sub(r'\n\s*\n\s*\n', '\n\n', remaining_content)
        
        if nested_rules:
            return f"{selector}{{{remaining_content}}}\n" + "\n".join(nested_rules)
        else:
            return match.group(0)
    
    # Process iteratively to handle deeply nested cases
    for _ in range(10):
        new_result = re.sub(rule_pattern, transform_rule, result, flags=re.MULTILINE | re.DOTALL)
        if new_result == result:
            break
        result = new_result
    
    return result


def _lossless_minify_css_string(css: str) -> str:
    """
    Remove comments and redundant whitespace without touching selectors/properties.

    This intentionally avoids aggressive rewrites so modern CSS (nesting, @layer, etc.)
    remains intact even when Lightning CSS is unavailable.
    """
    result: list[str] = []
    length = len(css)
    i = 0
    in_string = False
    string_char = ""
    pending_whitespace = False

    def needs_space(next_char: str) -> bool:
        if not result:
            return False
        prev = result[-1]
        separators = set(",:;>{}()[+-*/")
        return prev not in separators and next_char not in separators

    while i < length:
        char = css[i]

        if in_string:
            result.append(char)
            if char == "\\" and i + 1 < length:
                i += 1
                result.append(css[i])
            elif char == string_char:
                in_string = False
                string_char = ""
            i += 1
            continue

        if char in {"'", '"'}:
            if pending_whitespace and needs_space(char):
                result.append(" ")
            pending_whitespace = False
            in_string = True
            string_char = char
            result.append(char)
            i += 1
            continue

        if char == "/" and i + 1 < length and css[i + 1] == "*":
            i += 2
            while i + 1 < length and not (css[i] == "*" and css[i + 1] == "/"):
                i += 1
            i += 2
            continue

        if char in {" ", "\t", "\n", "\r", "\f"}:
            pending_whitespace = True
            i += 1
            continue

        if pending_whitespace and needs_space(char):
            result.append(" ")
        pending_whitespace = False
        result.append(char)
        i += 1

    return "".join(result)


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
            # Pattern to match @layer blocks: @layer name { ... }
            # This matches the entire block including nested braces
            layer_block_pattern = r'(@layer\s+\w+\s*\{)(.*?)(\})'
            
            # Pattern for @import statements
            import_pattern = r'@import\s+(?:url\()?\s*[\'"]([^\'"]+)[\'"]\s*(?:\))?\s*;'

            def resolve_import_in_context(import_match, layer_name=None):
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
                    
                    # Return the bundled content directly (it will be inserted into the @layer block)
                    return bundled_content
                except Exception as e:
                    logger.warning(
                        "css_import_read_failed",
                        imported_file=str(imported_file),
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    return import_match.group(0)

            # First, process @layer blocks that contain @import
            def process_layer_block(match):
                layer_decl = match.group(1)  # "@layer name {"
                layer_content = match.group(2)  # Content inside layer
                layer_close = match.group(3)  # "}"
                
                # Extract layer name
                layer_name_match = re.match(r'@layer\s+(\w+)', layer_decl)
                layer_name = layer_name_match.group(1) if layer_name_match else None
                
                # Process @import statements inside this layer
                processed_content = re.sub(
                    import_pattern,
                    lambda m: resolve_import_in_context(m, layer_name),
                    layer_content
                )
                
                # If we replaced any @imports, return the processed layer block
                # Otherwise, return original (might have other content)
                if processed_content != layer_content:
                    return f"{layer_decl}{processed_content}{layer_close}"
                return match.group(0)  # No changes

            # Process @layer blocks first
            result = re.sub(layer_block_pattern, process_layer_block, css_content, flags=re.DOTALL)
            
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
            # Transform CSS nesting before minifying (for browser compatibility)
            css_transformed = _transform_css_nesting(css_content)
            self._minified_content = _lossless_minify_css_string(css_transformed)
            global _warned_no_bundling
            if not _warned_no_bundling:
                logger.warning(
                    "lightningcss_unavailable",
                    info="CSS nesting will be transformed; minification without autoprefixing",
                    install_command="pip install lightningcss",
                )
                _warned_no_bundling = True

        except Exception as e:
            # If Lightning CSS fails unexpectedly, fall back to lossless minifier
            logger.warning(
                "lightningcss_processing_failed",
                error=str(e),
                error_type=type(e).__name__,
                fallback="lossless_css_minifier",
            )
            try:
                # Transform CSS nesting before minifying (for browser compatibility)
                css_transformed = _transform_css_nesting(css_content)
                self._minified_content = _lossless_minify_css_string(css_transformed)
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
            logger.debug("svg_optimization_skipped", source=str(self.source_path))
            self.optimized = True
            return

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
