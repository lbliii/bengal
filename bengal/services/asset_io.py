"""
Asset I/O service - pure functions for asset file operations.

Extracted from bengal.core.asset.asset_core to separate I/O from the Asset model.
All emit_diagnostic calls use context (typically the Asset) for sink resolution.

Functions:
    bundle_css: CSS @import resolution
    minify_css: CSS minification
    minify_js: JS minification (None if skip)
    hash_content_from_source: SHA256 fingerprint from asset content
    optimize_image: PIL Image or None
    copy_asset_to_output: Write asset to output directory
    cleanup_old_fingerprints: Remove stale fingerprinted siblings
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import uuid
from pathlib import Path
from re import Match
from typing import Any, Protocol

from bengal.assets.manifest import AssetManifest
from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.utils.io.atomic_write import atomic_write_text


class _HashableAsset(Protocol):
    """Protocol for asset-like objects used by hash_content_from_source."""

    _minified_content: str | None
    _bundled_content: str | None
    source_path: Path


def bundle_css(source_path: Path, context: Any | None = None) -> str:
    """
    Bundle CSS by resolving all @import statements recursively.

    Preserves @layer blocks when bundling @import statements.
    """
    import_pattern = r'@import\s+(?:url\()?\s*[\'"]([^\'"]+)[\'"]\s*(?:\))?\s*;'

    def resolve_import_in_context(
        import_match: Match[str], base_path: Path, layer_name: str | None = None
    ) -> str:
        import_path = import_match.group(1)
        imported_file = base_path / import_path

        if not imported_file.exists():
            return import_match.group(0)

        try:
            imported_content = imported_file.read_text(encoding="utf-8")
            bundled_content = _bundle_imports(imported_content, imported_file.parent, context)
            return bundled_content
        except (OSError, PermissionError) as e:
            emit_diagnostic(
                context,
                "warning",
                "css_import_read_failed",
                imported_file=str(imported_file),
                error=str(e),
                error_type=type(e).__name__,
            )
            return import_match.group(0)
        except Exception as e:
            emit_diagnostic(
                context,
                "error",
                "css_import_unexpected_error",
                imported_file=str(imported_file),
                error=str(e),
                error_type=type(e).__name__,
            )
            return import_match.group(0)

    def find_layer_block_end(css: str, start_pos: int) -> int:
        brace_count = 1
        i = start_pos
        in_string = False
        string_char = None

        while i < len(css) and brace_count > 0:
            char = css[i]

            if not in_string and char in ("'", '"'):
                in_string = True
                string_char = char
            elif in_string:
                if char == "\\" and i + 1 < len(css):
                    i += 2
                    continue
                if char == string_char:
                    in_string = False
                    string_char = None

            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1

            i += 1

        return i - 1 if brace_count == 0 else -1

    def process_layer_blocks(css: str, base_path: Path) -> str:
        result = []
        i = 0

        while i < len(css):
            layer_match = re.search(r"@layer\s+\w+\s*\{", css[i:])
            if not layer_match:
                result.append(css[i:])
                break

            layer_start = i + layer_match.start()
            result.append(css[i:layer_start])

            brace_pos = layer_start + layer_match.end() - 1
            layer_decl = css[layer_start : brace_pos + 1]

            layer_name_match = re.match(r"@layer\s+(\w+)", layer_decl)
            layer_name: str = layer_name_match.group(1) if layer_name_match else ""

            content_start = brace_pos + 1
            content_end = find_layer_block_end(css, content_start)

            if content_end == -1:
                result.append(css[layer_start:])
                break

            layer_content = css[content_start:content_end]
            current_layer = layer_name

            def layer_resolver(m: re.Match[str], layer: str = current_layer) -> str:
                return resolve_import_in_context(m, base_path, layer)

            processed_content = re.sub(
                import_pattern,
                layer_resolver,
                layer_content,
            )

            result.append(layer_decl)
            result.append(processed_content)
            result.append("}")

            i = content_end + 1

        return "".join(result)

    def _bundle_imports(css_content: str, base_path: Path, ctx: Any | None) -> str:
        result = process_layer_blocks(css_content, base_path)
        return re.sub(
            import_pattern,
            lambda m: resolve_import_in_context(m, base_path),
            result,
        )

    css_content = source_path.read_text(encoding="utf-8")
    return _bundle_imports(css_content, source_path.parent, context)


def minify_css(content: str, context: Any | None = None) -> str:
    """
    Minify CSS content using simple, safe minifier.

    Transforms CSS nesting first, then removes comments and whitespace.
    """
    from bengal.assets.css_minifier import minify_css as _minify_css
    from bengal.core.asset.css_transforms import transform_css_nesting

    try:
        css_content = transform_css_nesting(content)
        return _minify_css(css_content)
    except Exception as e:
        emit_diagnostic(
            context,
            "error",
            "css_minification_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return content


def minify_js(source_path: Path, context: Any | None = None) -> str | None:
    """
    Minify JavaScript content. Returns None if skipped (.min.js) or jsmin unavailable.
    """
    if source_path.name.endswith(".min.js"):
        return None
    try:
        from jsmin import jsmin

        js_content = source_path.read_text(encoding="utf-8")
        return jsmin(js_content)
    except ImportError:
        emit_diagnostic(context, "warning", "jsmin_unavailable", source=str(source_path))
        return None


def hash_content_from_source(asset: _HashableAsset) -> str:
    """
    Generate SHA256 fingerprint from asset content.

    Prefers minified content, then bundled, then source file.
    """
    hasher = hashlib.sha256()

    if asset._minified_content is not None:
        hasher.update(asset._minified_content.encode("utf-8"))
    elif asset._bundled_content is not None:
        hasher.update(asset._bundled_content.encode("utf-8"))
    else:
        with open(asset.source_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)

    return hasher.hexdigest()[:8]


def read_json_file(path: Path) -> dict[str, Any] | None:
    """
    Read JSON file. Returns None on error (invalid JSON, missing file).
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError, ValueError:
        return None


def write_json_file(path: Path, data: dict[str, Any], context: Any | None = None) -> bool:
    """
    Write JSON file atomically. Returns True on success.
    """
    try:
        content = json.dumps(data)
        atomic_write_text(path, content, encoding="utf-8", ensure_parent=True)
        return True
    except OSError:
        emit_diagnostic(
            context,
            "error",
            "json_write_failed",
            path=str(path),
        )
        return False


def load_pil_image(path: Path, context: Any | None = None) -> Any | None:
    """
    Load PIL Image from path. Returns None on ImportError or read failure.
    """
    try:
        from PIL import Image

        return Image.open(path)
    except ImportError:
        emit_diagnostic(context, "warning", "pillow_unavailable", source=str(path))
        return None
    except Exception as e:
        emit_diagnostic(
            context,
            "warning",
            "image_load_failed",
            source=str(path),
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def get_image_dimensions(path: Path, context: Any | None = None) -> tuple[int, int] | None:
    """
    Get image dimensions without loading full image. Returns (width, height) or None.
    """
    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.size
    except ImportError:
        emit_diagnostic(context, "warning", "pillow_unavailable", source=str(path))
        return None
    except Exception as e:
        emit_diagnostic(
            context,
            "warning",
            "image_load_failed",
            source=str(path),
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def save_pil_image(
    img: Any,
    path: Path,
    format: str,
    context: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Save PIL Image to path atomically. Returns True on success.
    """
    pid = os.getpid()
    tid = threading.get_ident()
    unique_id = uuid.uuid4().hex[:8]
    tmp_path = path.parent / f".{path.name}.{pid}.{tid}.{unique_id}.tmp"
    try:
        img.save(tmp_path, format=format.upper(), **kwargs)
        tmp_path.replace(path)
        return True
    except Exception as e:
        emit_diagnostic(
            context,
            "error",
            "image_save_failed",
            path=str(path),
            error=str(e),
            error_type=type(e).__name__,
        )
        tmp_path.unlink(missing_ok=True)
        return False


def optimize_image(source_path: Path, context: Any | None = None) -> Any | None:
    """
    Optimize image assets. Returns PIL Image or None (skip/fail).
    """
    if source_path.suffix.lower() == ".svg":
        emit_diagnostic(context, "debug", "svg_optimization_skipped", source=str(source_path))
        return None

    try:
        from PIL import Image
        from PIL.Image import Image as PILImage

        img: PILImage = Image.open(source_path)

        if img.mode in ("RGBA", "LA"):
            pass
        else:
            img = img.convert("RGB")

        return img
    except ImportError:
        emit_diagnostic(context, "warning", "pillow_unavailable", source=str(source_path))
        return None
    except Exception as e:
        emit_diagnostic(
            context,
            "warning",
            "image_optimization_failed",
            source=str(source_path),
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def copy_asset_to_output(
    asset: Any,
    output_dir: Path,
    use_fingerprint: bool,
    context: Any | None = None,
) -> Path:
    """
    Copy the asset to the output directory.

    Writes minified content, optimized image, or raw file atomically.
    """
    ctx = context if context is not None else asset

    if use_fingerprint:
        if not asset.fingerprint:
            asset.fingerprint = hash_content_from_source(asset)
        cleanup_old_fingerprints(asset, output_dir, ctx)

    if use_fingerprint and asset.fingerprint:
        out_name = f"{asset.source_path.stem}.{asset.fingerprint}{asset.source_path.suffix}"
    else:
        out_name = asset.source_path.name

    if asset.output_path:
        parent = (output_dir / asset.output_path).parent
        output_path = parent / out_name
    else:
        output_path = output_dir / out_name

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if asset._minified_content is not None:
        atomic_write_text(
            output_path,
            asset._minified_content,
            encoding="utf-8",
            ensure_parent=False,
        )
    elif asset._optimized_image is not None:
        pid = os.getpid()
        tid = threading.get_ident()
        unique_id = uuid.uuid4().hex[:8]
        tmp_path = output_path.parent / f".{output_path.name}.{pid}.{tid}.{unique_id}.tmp"
        try:
            ext = output_path.suffix.upper().lstrip(".")
            img_format = None
            if ext in ("JPG", "JPEG"):
                img_format = "JPEG"
            elif ext in ("PNG", "GIF", "WEBP"):
                img_format = ext

            asset._optimized_image.save(tmp_path, format=img_format, optimize=True, quality=85)
            tmp_path.replace(output_path)
        except Exception as e:
            emit_diagnostic(
                ctx,
                "error",
                "atomic_image_save_failed",
                path=str(output_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            tmp_path.unlink(missing_ok=True)
            raise
    else:
        pid = os.getpid()
        tid = threading.get_ident()
        unique_id = uuid.uuid4().hex[:8]
        tmp_path = output_path.parent / f".{output_path.name}.{pid}.{tid}.{unique_id}.tmp"
        try:
            shutil.copy2(asset.source_path, tmp_path)
            tmp_path.replace(output_path)
        except Exception as e:
            emit_diagnostic(
                ctx,
                "error",
                "atomic_asset_copy_failed",
                source=str(asset.source_path),
                target=str(output_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            tmp_path.unlink(missing_ok=True)
            raise

    asset.output_path = output_path
    return output_path


def cleanup_old_fingerprints(asset: Any, output_dir: Path, context: Any | None = None) -> None:
    """
    Remove outdated fingerprinted siblings before writing the new file.
    """
    try:
        site = getattr(asset, "_site", None)
        if site is not None and bool(getattr(site, "config", {}).get("_clean_output_this_run")):
            return

        parent = (output_dir / asset.output_path).parent if asset.output_path else output_dir

        if not parent.exists():
            return

        manifest_cleanup_done = False

        if site is not None:
            try:
                _bs = getattr(site, "build_state", None)
                prev: AssetManifest | None = (
                    getattr(_bs, "asset_manifest_previous", None)
                    if _bs is not None
                    else getattr(site, "_asset_manifest_previous", None)
                )
                if prev is not None and asset.logical_path is not None:
                    logical_str = asset.logical_path.as_posix()
                    prev_entry = prev.get(logical_str)
                    if prev_entry is not None and prev_entry.output_path:
                        old_full = Path(site.output_dir) / Path(prev_entry.output_path)
                        if (
                            old_full.exists()
                            and asset.fingerprint is not None
                            and not old_full.name.endswith(
                                f".{asset.fingerprint}{asset.source_path.suffix}"
                            )
                        ):
                            old_full.unlink(missing_ok=True)
                            manifest_cleanup_done = True
            except Exception:
                pass

        if manifest_cleanup_done:
            return

        pattern = f"{asset.source_path.stem}.*{asset.source_path.suffix}"
        for candidate in parent.glob(pattern):
            if asset.fingerprint and candidate.name.endswith(
                f".{asset.fingerprint}{asset.source_path.suffix}"
            ):
                continue
            candidate.unlink(missing_ok=True)
    except Exception as exc:
        emit_diagnostic(
            context if context is not None else asset,
            "debug",
            "asset_fingerprint_cleanup_failed",
            asset=str(asset.source_path),
            error=str(exc),
        )
