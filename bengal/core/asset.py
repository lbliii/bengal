"""
Asset Object - Handles images, CSS, JS, and other static files.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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

    This ensures browser compatibility for CSS nesting syntax.

    NOTE: We should NOT write nested CSS in source files. Use traditional selectors instead.
    This is a safety net for any nested CSS that slips through.
    """
    import re

    result = css

    # Pattern to match CSS rule blocks
    rule_pattern = r"([^{]+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"

    def transform_rule(match):
        selector = match.group(1).strip()
        block_content = match.group(2)

        # Skip @rules
        if selector.strip().startswith("@"):
            return match.group(0)

        # Clean @layer prefixes
        selector_clean = re.sub(r"^@layer\s+\w+\s*", "", selector).strip()
        has_layer = selector.strip().startswith("@layer")
        layer_decl = ""
        if has_layer:
            layer_match = re.match(r"(@layer\s+\w+)\s*", selector)
            if layer_match:
                layer_decl = layer_match.group(1) + " "

        if not selector_clean or selector_clean.startswith("@"):
            return match.group(0)

        # Find nested & selectors
        nested_pattern = r"&\s*([:.#\[\w\s-]+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        nested_rules = []

        def extract_nested(m):
            nested_selector_part = m.group(1).strip()
            nested_block = m.group(2)

            # Build full selector
            if (
                nested_selector_part.startswith(":")
                or nested_selector_part.startswith(".")
                or nested_selector_part.startswith("[")
                or nested_selector_part.startswith(" ")
            ):
                full_selector = selector_clean + nested_selector_part
            else:
                full_selector = selector_clean + nested_selector_part

            if has_layer:
                nested_rules.append(f"{layer_decl}{full_selector} {{{nested_block}}}")
            else:
                nested_rules.append(f"{full_selector} {{{nested_block}}}")
            return ""

        remaining_content = re.sub(
            nested_pattern, extract_nested, block_content, flags=re.MULTILINE
        )
        remaining_content = re.sub(r"\n\s*\n\s*\n", "\n\n", remaining_content)

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


def _remove_duplicate_bare_h1_rules(css: str) -> str:
    """
    Remove duplicate bare h1 rules that appear right after scoped h1 rules.

    CSS processing sometimes creates duplicate rules like:
        .browser-header h1 { font-size: var(--text-5xl); }
        h1 { font-size: var(--text-5xl); }  # Duplicate!

    The bare h1 rule overrides the base typography rule, breaking text sizing.
    This function removes the duplicate bare h1 rules.
    """
    import re

    # Pattern to match: scoped selector h1 { ... } followed by bare h1 { ... }
    # We need to match the scoped rule, then check if there's a duplicate bare h1
    pattern = r"(\.[\w-]+\s+h1\s*\{[^}]+\})\s*(h1\s*\{[^}]+\})"

    def remove_duplicate(match):
        scoped_rule = match.group(1)
        bare_rule = match.group(2)

        # Extract content from both rules
        scoped_content_match = re.search(r"\{([^}]+)\}", scoped_rule, re.DOTALL)
        bare_content_match = re.search(r"\{([^}]+)\}", bare_rule, re.DOTALL)

        if scoped_content_match and bare_content_match:
            scoped_content = (
                scoped_content_match.group(1).strip().replace(" ", "").replace("\n", "")
            )
            bare_content = bare_content_match.group(1).strip().replace(" ", "").replace("\n", "")

            # If content is identical, remove the bare rule
            if scoped_content == bare_content:
                return scoped_rule  # Return only the scoped rule

        # Not a duplicate, keep both
        return match.group(0)

    # Process iteratively to catch all duplicates
    result = css
    for _ in range(5):  # Max 5 iterations
        new_result = re.sub(pattern, remove_duplicate, result, flags=re.DOTALL)
        if new_result == result:
            break
        result = new_result

    return result


def _lossless_minify_css_string(css: str) -> str:
    """
    Remove comments and redundant whitespace without touching selectors/properties.

    This intentionally avoids aggressive rewrites so modern CSS (nesting, @layer, etc.)
    remains intact.
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

        # Preserve space before number sequences ending in % (for CSS functions like color-mix)
        # Check if current char is digit and look ahead to see if % follows the number
        if char.isdigit() and pending_whitespace:
            # Look ahead to find where the number sequence ends
            j = i
            while j < length and (css[j].isdigit() or css[j] == "."):
                j += 1
            # If the sequence ends with %, preserve the space
            if j < length and css[j] == "%":
                result.append(" ")
                pending_whitespace = False

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
    logical_path: Path | None = None

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

                    # Return bundled content so it can replace the @layer block body
                    return bundled_content
                except Exception as e:
                    logger.warning(
                        "css_import_read_failed",
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
                    layer_name = layer_name_match.group(1) if layer_name_match else None

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
                    processed_content = re.sub(
                        import_pattern,
                        lambda m, layer=layer_name: resolve_import_in_context(m, layer),
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
        # Get the CSS content (bundled if this is an entry point)
        if hasattr(self, "_bundled_content"):
            css_content = self._bundled_content
        else:
            with open(self.source_path, encoding="utf-8") as f:
                css_content = f.read()

        try:
            # Transform CSS nesting first (for browser compatibility)
            css_content = _transform_css_nesting(css_content)

            from bengal.utils.css_minifier import minify_css

            # Simple minification: remove comments and whitespace only
            # No transformations that could break CSS
            self._minified_content = minify_css(css_content)
        except Exception as e:
            logger.error(
                "css_minification_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # On error, use original content (fail-safe)
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

    def _hash_source_chunks(self) -> Iterator[bytes]:
        """
        Yield byte chunks representing the content that should drive fingerprinting.

        Prefers minified (or bundled) content so hashes match the bytes we actually emit.
        Falls back to the original file contents when no in-memory transform exists.
        """
        if hasattr(self, "_minified_content") and isinstance(self._minified_content, str):
            yield self._minified_content.encode("utf-8")
            return

        if hasattr(self, "_bundled_content") and isinstance(self._bundled_content, str):
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

    def _cleanup_old_fingerprints_prepare(self, output_dir: Path) -> None:
        """
        Remove outdated fingerprinted siblings before writing the new file.

        This ensures only one fingerprinted version exists at a time, preventing
        stale files from being served.

        Args:
            output_dir: Output directory where assets are written
        """
        try:
            # Determine where the file will be written
            parent = (output_dir / self.output_path).parent if self.output_path else output_dir

            if not parent.exists():
                return  # Directory doesn't exist yet, nothing to clean

            # Find all existing fingerprinted versions of this asset
            pattern = f"{self.source_path.stem}.*{self.source_path.suffix}"
            for candidate in parent.glob(pattern):
                # Skip if this is the file we're about to write (fingerprint already generated)
                if self.fingerprint and candidate.name.endswith(
                    f".{self.fingerprint}{self.source_path.suffix}"
                ):
                    continue
                # Remove stale fingerprint (any file matching the pattern that isn't the current one)
                candidate.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logger.debug(
                "asset_fingerprint_cleanup_failed",
                asset=str(self.source_path),
                error=str(exc),
            )

    def __repr__(self) -> str:
        return f"Asset(type='{self.asset_type}', source='{self.source_path.name}')"
