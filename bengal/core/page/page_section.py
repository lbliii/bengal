"""
Page Section Mixin - Section reference and path formatting.

Provides _section property (lazy lookup via path or URL), section_path,
and _format_path_for_log for display. Section references are stable across
rebuilds when Section objects are recreated.

See Also:
- plan/active/rfc-page-section-reference-contract.md
- bengal/core/page/__init__.py: Page class that uses this mixin
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.protocols import SiteLike

if TYPE_CHECKING:
    from bengal.core.section import Section
    from bengal.core.site import Site


class PageSectionMixin:
    """
    Mixin providing section reference and path formatting.

    Handles:
    - _section: Lazy section lookup (path or URL-based)
    - section_path: Section path as string
    - _format_path_for_log: Path formatting for diagnostics
    """

    # Declare attributes provided by the dataclass
    source_path: Path
    _site: Site | None
    _section_path: Path | None
    _section_url: str | None
    _section_obj_cache: Section | object | None
    _section_obj_cache_key: tuple[int, int, Path | None, str | None] | None
    _cached_section_path_str: str | None

    # Provided by Page class
    _SECTION_NOT_FOUND: ClassVar[object]
    _global_missing_section_warnings: ClassVar[dict[str, int]]
    _warnings_lock: ClassVar[threading.Lock]
    _MAX_WARNING_KEYS: ClassVar[int]

    def _format_path_for_log(self, path: Path | str | None) -> str | None:
        """
        Format a path as relative to site root for logging.

        Makes paths relative to the site root directory to avoid showing
        user-specific absolute paths in logs and warnings.

        Args:
            path: Path to format (can be Path, str, or None)

        Returns:
            Relative path string, or None if path was None
        """
        from bengal.utils.primitives.text import format_path_for_display

        base_path = None
        if self._site is not None and isinstance(self._site, SiteLike):
            base_path = self._site.root_path

        return format_path_for_display(path, base_path)

    @property
    def _section(self) -> Section | None:
        """
        Get the section this page belongs to (lazy lookup via path or URL).

        Cost: O(1) cached — first access O(1) registry lookup.

        Virtual sections (path=None) use URL-based lookups via _section_url.
        Regular sections use path-based lookups via _section_path.
        """
        # No section reference at all
        if self._section_path is None and self._section_url is None:
            return None

        if self._site is None:
            warn_key = "missing_site"
            with self._warnings_lock:
                if self._global_missing_section_warnings.get(warn_key, 0) < 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_lookup_no_site",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                    )
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = (
                        self._global_missing_section_warnings.get(warn_key, 0) + 1
                    )
            return None

        epoch = self._site.registry.epoch if hasattr(self._site, "registry") else 0
        cache_key = (id(self._site), epoch, self._section_path, self._section_url)
        if self._section_obj_cache_key == cache_key:
            cached = self._section_obj_cache
            return None if cached is self._SECTION_NOT_FOUND else cached

        if self._section_path is not None:
            section = self._site.get_section_by_path(self._section_path)
        else:
            section = self._site.get_section_by_url(self._section_url)

        if section is None:
            warn_key = str(self._section_path or self._section_url)
            with self._warnings_lock:
                count = self._global_missing_section_warnings.get(warn_key, 0)

                if count < 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_not_found",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                        count=count + 1,
                    )
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = count + 1
                elif count == 3:
                    emit_diagnostic(
                        self,
                        "warning",
                        "page_section_not_found_summary",
                        page=self._format_path_for_log(self.source_path),
                        section_path=self._format_path_for_log(self._section_path),
                        section_url=self._section_url,
                        total_warnings=count + 1,
                        note="Further warnings for this section will be suppressed",
                    )
                    if len(self._global_missing_section_warnings) >= self._MAX_WARNING_KEYS:
                        first_key = next(iter(self._global_missing_section_warnings))
                        del self._global_missing_section_warnings[first_key]
                    self._global_missing_section_warnings[warn_key] = count + 1

        self._section_obj_cache_key = cache_key
        self._section_obj_cache = section if section is not None else self._SECTION_NOT_FOUND
        return section

    @_section.setter
    def _section(self, value: Section | None) -> None:
        """
        Set the section this page belongs to (stores path or URL, not object).

        For virtual sections (path=None), stores relative_url in _section_url.
        For regular sections, stores path in _section_path.
        """
        if value is None:
            self._section_path = None
            self._section_url = None
        elif value.path is not None:
            self._section_path = value.path
            self._section_url = None
        else:
            self._section_path = None
            self._section_url = getattr(value, "_path", None) or f"/{value.name}/"

        self._section_obj_cache_key = None
        self._section_obj_cache = None
        self._cached_section_path_str = None

    @property
    def section_path(self) -> str | None:
        """
        Get the section path as a string.

        Cost: O(1) — direct field read.
        """
        return str(self._section_path) if self._section_path else None
