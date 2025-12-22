"""
SwizzleManager - Safe template override management for themes.

Provides a "swizzle" system for safely overriding theme templates while
tracking provenance and enabling updates. Inspired by similar patterns
in Docusaurus and other documentation frameworks.

Key Features:
    - Copy theme templates into project `templates/` preserving paths
    - Track provenance in `.bengal/themes/sources.json`
    - List all swizzled files with their source themes
    - Auto-update unchanged files when themes are updated
    - Detect local modifications to prevent accidental overwrites

Workflow:
    1. User runs `bengal swizzle partials/toc.html`
    2. Template is copied from theme to project templates/
    3. Provenance is recorded (source, checksums, timestamp)
    4. User modifies the local copy as needed
    5. Later, `bengal swizzle --update` syncs unchanged files

Design Note:
    Currently uses naive update (only updates if local unchanged).
    Three-way merge support may be added in future versions.

Usage:
    >>> from bengal.utils.swizzle import SwizzleManager
    >>>
    >>> manager = SwizzleManager(site)
    >>>
    >>> # Swizzle a template
    >>> path = manager.swizzle("partials/toc.html")
    >>>
    >>> # List swizzled files
    >>> for record in manager.list():
    ...     print(f"{record.target} from {record.theme}")
    >>>
    >>> # Update unchanged files
    >>> results = manager.update()

Related Modules:
    - bengal/cli/commands/swizzle.py: CLI command
    - bengal/rendering/engines.py: Template engine with swizzle support
    - bengal/core/theme.py: Theme resolution

See Also:
    - .bengal/themes/sources.json: Swizzle registry location
"""

from __future__ import annotations

import builtins
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.hashing import hash_file, hash_str
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site

logger = get_logger(__name__)


@dataclass(frozen=True)
class SwizzleRecord:
    """
    Immutable record of a swizzled template's provenance.

    Tracks the origin of a swizzled file and checksums for detecting
    local modifications. Stored in `.bengal/themes/sources.json`.

    Attributes:
        target: Relative path within project templates/ (e.g., "partials/toc.html").
        source: Absolute path to original theme file at swizzle time.
        theme: Theme name at time of swizzle (e.g., "default", "docs-pro").
        upstream_checksum: SHA-256 checksum (truncated) of original theme file.
        local_checksum: SHA-256 checksum (truncated) of copied file at swizzle time.
        timestamp: Unix epoch seconds when swizzle occurred.
    """

    target: str  # templates-relative path (e.g., "partials/toc.html")
    source: str  # absolute path to theme file used for swizzle
    theme: str  # theme name at time of swizzle
    upstream_checksum: str  # checksum of upstream file when swizzled
    local_checksum: str  # checksum of copied local file at swizzle time
    timestamp: float  # epoch seconds


class SwizzleManager:
    """
    Manages safe template overrides with provenance tracking.

    The SwizzleManager enables users to customize theme templates while
    maintaining a record of where they came from. This allows for safe
    theme updates - unchanged swizzled files can be auto-updated.

    Attributes:
        site: Site instance for theme and path resolution.
        root: Site root path.
        registry_path: Path to `.bengal/themes/sources.json`.

    Example:
        >>> manager = SwizzleManager(site)
        >>>
        >>> # Swizzle a template for customization
        >>> local_path = manager.swizzle("partials/header.html")
        >>> print(f"Edit: {local_path}")
        >>>
        >>> # Check what's been swizzled
        >>> for record in manager.list():
        ...     print(f"{record.target} (from {record.theme})")
        >>>
        >>> # Update unchanged swizzles after theme update
        >>> results = manager.update()
        >>> print(f"Updated: {results['updated']}")
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize the SwizzleManager.

        Args:
            site: Site instance with root_path and paths configured.
        """
        self.site = site
        self.root = site.root_path
        self.registry_path = site.paths.swizzle_registry

    def swizzle(self, template_rel_path: str) -> Path:
        """
        Copy a theme template into project templates/ and record provenance.

        Finds the template in the theme chain, copies it to the project's
        templates/ directory preserving the relative path, and records
        provenance information for future updates.

        Args:
            template_rel_path: Relative path inside theme templates/
                (e.g., 'partials/toc.html', 'layouts/default.html').

        Returns:
            Path to the copied file under project templates/.

        Raises:
            FileNotFoundError: If template not found in any theme.

        Example:
            >>> path = manager.swizzle("partials/toc.html")
            >>> path
            PosixPath('/mysite/templates/partials/toc.html')
        """
        logger.debug(
            "swizzle_start",
            template=template_rel_path,
            theme=self.site.theme or "default",
            site_root=str(self.root),
        )

        source = self._find_theme_template(template_rel_path)
        if not source or not source.exists():
            logger.error(
                "swizzle_template_not_found",
                template=template_rel_path,
                theme=self.site.theme,
                resolved_source=str(source) if source else None,
            )
            raise FileNotFoundError(f"Template not found in theme chain: {template_rel_path}")

        dest = self.root / "templates" / template_rel_path

        # Check if re-swizzling (overwriting existing)
        is_reswizzle = dest.exists()
        if is_reswizzle:
            logger.info("swizzle_overwriting_existing", template=template_rel_path, dest=str(dest))

        dest.parent.mkdir(parents=True, exist_ok=True)

        content = source.read_text(encoding="utf-8")
        dest.write_text(content, encoding="utf-8")

        upstream_checksum = _checksum_str(content)
        local_checksum = _checksum_file(dest)

        record = SwizzleRecord(
            target=str(dest.relative_to(self.root / "templates")),
            source=str(source),
            theme=self.site.theme or "default",
            upstream_checksum=upstream_checksum,
            local_checksum=local_checksum,
            timestamp=time.time(),
        )
        self._save_record(record)
        logger.info(
            "swizzle_copied",
            target=record.target,
            source=record.source,
            theme=record.theme,
            is_reswizzle=is_reswizzle,
        )
        return dest

    def list(self) -> builtins.list[SwizzleRecord]:
        """
        List all swizzled templates.

        Loads the registry and returns all valid swizzle records.
        Invalid records (malformed JSON) are logged and skipped.

        Returns:
            List of SwizzleRecord objects for all swizzled templates.

        Example:
            >>> for record in manager.list():
            ...     print(f"{record.target}: from {record.theme}")
            partials/toc.html: from default
            layouts/single.html: from docs-pro
        """
        data = self._load_registry()
        records: list[SwizzleRecord] = []
        invalid_count = 0
        for rec in data.get("records", []):
            try:
                records.append(SwizzleRecord(**rec))
            except Exception as e:
                invalid_count += 1
                logger.warning(
                    "swizzle_invalid_record", record=rec, error=str(e), error_type=type(e).__name__
                )
                continue

        logger.debug("swizzle_list", total=len(records), invalid=invalid_count)
        return records

    def list_swizzled(self) -> builtins.list[SwizzleRecord]:
        """
        Alias for list() for backward compatibility.

        Returns:
            List of SwizzleRecord objects.
        """
        return self.list()

    def update(self) -> dict[str, int]:
        """
        Update swizzled files from upstream if local is unchanged.

        Attempts to update each swizzled file from its upstream theme source.
        Only updates files where the local checksum matches the original
        swizzle checksum (i.e., user hasn't modified the file).

        Returns:
            Dictionary with update counts:
                - updated (int): Files successfully updated
                - skipped_changed (int): Files skipped (local modifications)
                - missing_upstream (int): Files skipped (theme source not found)

        Example:
            >>> results = manager.update()
            >>> print(f"Updated {results['updated']} files")
            >>> print(f"Skipped {results['skipped_changed']} modified files")
        """
        data = self._load_registry()
        records = data.get("records", [])
        logger.info("swizzle_update_start", total_records=len(records))

        updated = 0
        skipped_changed = 0
        missing_upstream = 0

        for rec in records:
            target_path = self.root / "templates" / rec.get("target", "")
            source_path = Path(rec.get("source", ""))

            if not source_path.exists():
                # Try resolving again (theme might have moved)
                resolved = self._find_theme_template(rec.get("target", ""))
                if not resolved:
                    missing_upstream += 1
                    logger.warning(
                        "swizzle_update_missing_upstream",
                        target=rec.get("target"),
                        source=str(source_path),
                    )
                    continue
                source_path = resolved
                logger.debug(
                    "swizzle_update_resolved",
                    target=rec.get("target"),
                    old_source=rec.get("source"),
                    new_source=str(resolved),
                )

            # Only overwrite if local file is unchanged since swizzle time
            if not target_path.exists():
                skipped_changed += 1
                logger.warning(
                    "swizzle_update_local_missing", target=rec.get("target"), path=str(target_path)
                )
                continue

            current_checksum = _checksum_file(target_path)
            expected_checksum = rec.get("local_checksum")
            if current_checksum != expected_checksum:
                skipped_changed += 1
                logger.info(
                    "swizzle_update_skipped_changed",
                    target=rec.get("target"),
                    reason="local_modifications_detected",
                )
                continue

            new_content = source_path.read_text(encoding="utf-8")
            target_path.write_text(new_content, encoding="utf-8")

            # Update checksums
            rec["upstream_checksum"] = _checksum_str(new_content)
            rec["local_checksum"] = _checksum_str(new_content)
            rec["timestamp"] = time.time()
            updated += 1
            logger.info("swizzle_update_success", target=rec.get("target"), source=str(source_path))

        # Persist registry updates
        data["records"] = records
        self._write_registry(data)

        logger.info(
            "swizzle_update_complete",
            updated=updated,
            skipped_changed=skipped_changed,
            missing_upstream=missing_upstream,
        )
        return {
            "updated": updated,
            "skipped_changed": skipped_changed,
            "missing_upstream": missing_upstream,
        }

    # Internal helpers

    def _is_modified(self, template_rel_path: str) -> bool:
        """Check if a swizzled template has been modified locally.

        Args:
            template_rel_path: Relative path inside templates/ (e.g., 'partials/toc.html')

        Returns:
            True if template has been modified locally, False otherwise
        """
        data = self._load_registry()
        records = data.get("records", [])

        # Find record for this template
        record = None
        for rec in records:
            if rec.get("target") == template_rel_path:
                record = rec
                break

        if not record:
            return False  # Not swizzled, so not modified

        target_path = self.root / "templates" / template_rel_path
        if not target_path.exists():
            return False  # File doesn't exist, not modified

        current_checksum = _checksum_file(target_path)
        expected_checksum = record.get("local_checksum")

        return bool(current_checksum != expected_checksum)

    def _find_theme_template(self, template_rel_path: str) -> Path | None:
        try:
            from bengal.rendering.engines import create_engine

            engine = create_engine(self.site)
            return engine.get_template_path(template_rel_path)
        except Exception as e:
            logger.warning("swizzle_resolve_failed", template=template_rel_path, error=str(e))
            return None

    def _save_record(self, record: SwizzleRecord) -> None:
        data = self._load_registry()
        rec_dict = {
            "target": record.target,
            "source": record.source,
            "theme": record.theme,
            "upstream_checksum": record.upstream_checksum,
            "local_checksum": record.local_checksum,
            "timestamp": record.timestamp,
        }
        # Replace existing entry with same target
        existing = data.get("records", [])
        filtered = [r for r in existing if r.get("target") != record.target]
        filtered.append(rec_dict)
        data["records"] = filtered
        self._write_registry(data)

    def _load_registry(self) -> dict[str, Any]:
        try:
            if self.registry_path.exists():
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                logger.debug(
                    "swizzle_registry_loaded",
                    path=str(self.registry_path),
                    record_count=len(data.get("records", [])),
                )
                return dict(data) if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            logger.error(
                "swizzle_registry_json_invalid",
                path=str(self.registry_path),
                error=str(e),
                error_type="JSONDecodeError",
            )
        except Exception as e:
            logger.error(
                "swizzle_registry_load_failed",
                path=str(self.registry_path),
                error=str(e),
                error_type=type(e).__name__,
            )
        return {"records": []}

    def _write_registry(self, data: dict[str, Any]) -> None:
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            self.registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.debug(
                "swizzle_registry_saved",
                path=str(self.registry_path),
                record_count=len(data.get("records", [])),
            )
        except Exception as e:
            logger.error(
                "swizzle_registry_save_failed",
                path=str(self.registry_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


def _checksum_file(path: Path) -> str:
    """Compute truncated checksum of file content."""
    try:
        return hash_file(path, truncate=16)
    except Exception as e:
        logger.debug(
            "swizzle_checksum_file_failed",
            path=str(path),
            error=str(e),
            error_type=type(e).__name__,
            action="returning_empty_string",
        )
        return ""


def _checksum_str(content: str) -> str:
    """Compute truncated checksum of string content."""
    return hash_str(content, truncate=16)
