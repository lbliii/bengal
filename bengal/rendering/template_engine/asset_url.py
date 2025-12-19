"""
Asset URL generation for template engine.

Provides asset URL generation with fingerprinting, manifest lookup,
and file:// protocol support.

Related Modules:
    - bengal.rendering.template_engine.core: Uses these helpers
    - bengal.assets.manifest: Asset manifest handling
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from bengal.rendering.template_engine.url_helpers import with_baseurl
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def normalize_and_validate_asset_path(raw_path: str) -> str:
    """
    Normalize and validate the provided asset path to prevent traversal/absolute paths.

    Args:
        raw_path: Raw asset path from template

    Returns:
        Sanitized asset path, or empty string if invalid
    """
    # Convert Windows-style separators and trim whitespace
    candidate = (raw_path or "").replace("\\", "/").strip()
    # Remove any leading slash to keep it relative inside /assets
    while candidate.startswith("/"):
        candidate = candidate[1:]

    try:
        posix_path = PurePosixPath(candidate)
    except Exception as e:
        logger.debug(
            "asset_url_path_parse_failed",
            candidate=candidate,
            error=str(e),
            error_type=type(e).__name__,
        )
        return ""

    # Reject absolute paths and traversal segments
    if posix_path.is_absolute() or any(part == ".." for part in posix_path.parts):
        return ""

    # Collapse any '.' segments by reconstructing the path
    sanitized = PurePosixPath(*[p for p in posix_path.parts if p not in ("", ".")])
    return sanitized.as_posix()


def compute_relative_asset_path(
    asset_path: str,
    page_context: Any,
    output_dir: Path,
) -> str | None:
    """
    Compute relative path from page to asset for file:// protocol.

    Args:
        asset_path: Asset path (e.g., 'assets/css/style.css')
        page_context: Page context with output_path
        output_dir: Site output directory

    Returns:
        Relative path string, or None if cannot compute
    """
    if not page_context or not hasattr(page_context, "output_path") or not page_context.output_path:
        return None

    try:
        page_rel_to_root = page_context.output_path.relative_to(output_dir)
        depth = len(page_rel_to_root.parent.parts) if page_rel_to_root.parent != Path(".") else 0
        if depth > 0:
            relative_prefix = "/".join([".."] * depth)
            return f"{relative_prefix}/{asset_path}"
        else:
            return f"./{asset_path}"
    except (ValueError, AttributeError):
        return None


class AssetURLMixin:
    """
    Mixin providing asset URL generation for TemplateEngine.

    Requires these attributes on the host class:
        - site: Site instance
        - _asset_manifest_path: Path

    Requires these methods from ManifestHelpersMixin (must come BEFORE this mixin in MRO):
        - _get_manifest_entry(logical_path: str) -> AssetManifestEntry | None
        - _warn_manifest_fallback(logical_path: str) -> None
    """

    site: Any
    _asset_manifest_path: Path
    _asset_manifest_present: bool
    _fingerprinted_asset_cache: dict[str, str | None]

    # NOTE: Do NOT add stub methods here for _get_manifest_entry, _warn_manifest_fallback.
    # ManifestHelpersMixin must come BEFORE this mixin in class bases to provide them.
    # Adding stubs would shadow the real implementations if MRO order is wrong.

    def _asset_url(self, asset_path: str, page_context: Any = None) -> str:
        """
        Generate URL for an asset.

        Handles:
        - Manifest lookup for fingerprinted assets
        - file:// protocol with relative paths
        - Dev server mode (no fingerprints)
        - Fallback to direct asset paths

        Args:
            asset_path: Path to asset file
            page_context: Optional page context for computing relative paths

        Returns:
            Asset URL
        """
        safe_asset_path = normalize_and_validate_asset_path(asset_path)
        if not safe_asset_path:
            logger.warning("asset_path_invalid", provided=str(asset_path))
            return "/assets/"

        baseurl_value = (self.site.config.get("baseurl", "") or "").rstrip("/")

        # Handle file:// protocol - generate relative URLs
        if baseurl_value.startswith("file://"):
            return self._asset_url_file_protocol(safe_asset_path, page_context)

        # In dev server mode, prefer stable URLs without fingerprints
        try:
            if self.site.dev_mode:
                return with_baseurl(f"/assets/{safe_asset_path}", self.site)
        except Exception as e:
            logger.debug(
                "dev_server_asset_url_failed",
                asset_path=safe_asset_path,
                error=str(e),
                error_type=type(e).__name__,
            )

        # Use manifest for fingerprinted asset resolution
        manifest_entry = self._get_manifest_entry(safe_asset_path)
        if manifest_entry:
            return with_baseurl(f"/{manifest_entry.output_path}", self.site)

        # Warn if manifest exists but entry missing
        if getattr(self, "_asset_manifest_present", False):
            self._warn_manifest_fallback(safe_asset_path)

        # Fallback: check output directory for fingerprinted files
        fingerprinted = self._find_fingerprinted_asset(safe_asset_path)
        if fingerprinted:
            return with_baseurl(f"/assets/{fingerprinted}", self.site)

        # Final fallback: return direct asset path
        return with_baseurl(f"/assets/{safe_asset_path}", self.site)

    def _asset_url_file_protocol(self, safe_asset_path: str, page_context: Any) -> str:
        """
        Generate asset URL for file:// protocol using relative paths.

        Args:
            safe_asset_path: Validated asset path
            page_context: Page context for computing relative path

        Returns:
            Relative asset URL
        """
        asset_url_path = f"assets/{safe_asset_path}"

        # Try to compute relative path from page
        relative_path = compute_relative_asset_path(
            asset_url_path, page_context, self.site.output_dir
        )
        if relative_path:
            return relative_path

        # Fallback: assume root-level
        return f"./{asset_url_path}"

    def _find_fingerprinted_asset(self, safe_asset_path: str) -> str | None:
        """
        Find fingerprinted version of asset in output directory.

        Args:
            safe_asset_path: Validated asset path

        Returns:
            Fingerprinted asset path if found, None otherwise
        """
        # Performance: globbing for every `asset_url()` call is expensive. Cache per
        # TemplateEngine instance (thread-local in parallel builds).
        if safe_asset_path in getattr(self, "_fingerprinted_asset_cache", {}):
            return self._fingerprinted_asset_cache[safe_asset_path]

        asset_path_obj = PurePosixPath(safe_asset_path)
        output_asset_dir = self.site.output_dir / "assets" / asset_path_obj.parent
        output_asset_name = asset_path_obj.name

        if not output_asset_dir.exists():
            self._fingerprinted_asset_cache[safe_asset_path] = None
            return None

        # Look for fingerprinted version (e.g., style.12345678.css)
        if "." in output_asset_name:
            base_name, ext = output_asset_name.rsplit(".", 1)
            pattern = f"{base_name}.*.{ext}"
        else:
            pattern = f"{output_asset_name}.*"

        match = next(output_asset_dir.glob(pattern), None)
        if match is not None:
            result: str | None = str(asset_path_obj.parent / match.name)
        else:
            result = None

        self._fingerprinted_asset_cache[safe_asset_path] = result
        return result
