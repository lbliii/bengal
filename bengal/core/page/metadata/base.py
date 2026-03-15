"""
Page metadata base mixin - metadata view, frontmatter, and core flags.

Provides the metadata property (CascadeView), frontmatter access, and
simple flags (is_virtual, template_name, prerendered_html, relative_path).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from bengal.core.cascade import CascadeSnapshot, CascadeView
from bengal.core.page.frontmatter import Frontmatter

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.site import Site


class PageMetadataBaseMixin:
    """Base metadata: metadata view, frontmatter, virtual/template flags."""

    _raw_metadata: dict[str, Any]
    source_path: Path
    output_path: Path | None
    _section_path: Path | None
    _cached_section_path_str: str | None
    _metadata_view_cache: CascadeView | None
    _metadata_view_cache_key: tuple[int, str] | None
    _frontmatter: Frontmatter | None
    _virtual: bool
    _prerendered_html: str | None
    _template_name: str | None
    _site: Site | None

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Return combined frontmatter + cascade metadata as CascadeView.

        Cost: O(1) cached after first access per cascade snapshot. First access
        with _cached_section_path_str unset: O(n) pathlib.relative_to.

        Hot-path alternative: page.identity for boolean flags and pre-computed strings.
        """
        if self._site is None:
            return self._raw_metadata

        cascade = getattr(self._site, "cascade", None)
        if cascade is None or not isinstance(cascade, CascadeSnapshot):
            return self._raw_metadata

        section_path = self._cached_section_path_str
        if section_path is None:
            if self._section_path:
                try:
                    content_dir = self._site.root_path / "content"
                    section_path = str(self._section_path.relative_to(content_dir))
                except ValueError, AttributeError:
                    section_path = str(self._section_path)
            else:
                section_path = ""
            self._cached_section_path_str = section_path

        cache_key = (id(cascade), section_path)
        if self._metadata_view_cache is not None and self._metadata_view_cache_key == cache_key:
            return self._metadata_view_cache

        view = CascadeView.for_page(
            frontmatter=self._raw_metadata,
            section_path=section_path,
            snapshot=cascade,
        )
        self._metadata_view_cache = view
        self._metadata_view_cache_key = cache_key
        return view

    @property
    def is_virtual(self) -> bool:
        """Check if this is a virtual page (not backed by a disk file).

        Cost: O(1) — direct field read.
        """
        return self._virtual

    @property
    def template_name(self) -> str | None:
        """Get custom template name for this page.

        Cost: O(1) — direct field read.
        """
        return self._template_name

    @property
    def prerendered_html(self) -> str | None:
        """Get pre-rendered HTML for virtual pages.

        Cost: O(1) — direct field read.
        """
        return self._prerendered_html

    @property
    def frontmatter(self) -> Frontmatter:
        """Typed access to frontmatter fields.

        Cost: O(1) cached — first access O(n) for metadata keys via Frontmatter.from_dict.
        """
        if self._frontmatter is None:
            self._frontmatter = Frontmatter.from_dict(self.metadata)
        return self._frontmatter

    @property
    def relative_path(self) -> str:
        """Get relative path string (alias for source_path as string).

        Cost: O(1) — direct field read.
        """
        return str(self.source_path)
