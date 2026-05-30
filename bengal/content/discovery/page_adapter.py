"""Adapters from immutable discovery records to Page compatibility objects."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bengal.core.records import SourcePage
    from bengal.protocols import PageLike, SectionLike


def _load_page_class() -> type[Any]:
    """Load the remaining mutable Page class only at the adapter boundary."""
    return cast("type[Any]", import_module("bengal.core.page").Page)


def page_from_source_page(
    source_page: SourcePage,
    *,
    site: Any | None = None,
    section: SectionLike | None = None,
    output_path: Path | None = None,
    rendered_html: str | None = None,
    template_name: str | None = None,
    from_cache: bool = False,
) -> PageLike:
    """Adapt a ``SourcePage`` into the temporary mutable ``Page`` surface.

    ``SourcePage`` remains the discovery boundary record. This helper keeps the
    remaining ``Page`` construction isolated while downstream code still expects
    the compatibility object.
    """
    page = _load_page_class()(
        source_path=Path(source_page.source_path),
        _raw_content=source_page.raw_content,
        _raw_metadata=source_page.raw_metadata_dict(),
        rendered_html=rendered_html or "",
        output_path=output_path,
        _from_cache=from_cache,
    )

    if from_cache:
        page.core = source_page.core

    page.virtual = source_page.is_virtual

    if rendered_html is not None:
        page.prerendered_html = rendered_html
    if template_name is not None:
        page.template_name = template_name

    if site is not None:
        page._site = site
    if section is not None:
        page._section = section
    elif source_page.core.section:
        page._section_path = Path(source_page.core.section)

    if source_page.lang:
        page.lang = source_page.lang
    if source_page.translation_key:
        page.translation_key = source_page.translation_key

    return cast("PageLike", page)
