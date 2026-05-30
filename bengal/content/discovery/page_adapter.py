"""Adapters from immutable discovery records to Page compatibility objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bengal.core.page.runtime import RuntimePage
from bengal.core.page_site import set_page_site
from bengal.core.section.utils import set_page_section

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.core.records import SourcePage
    from bengal.protocols import PageLike, SectionLike


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
    page = RuntimePage.from_source_page(
        source_page,
        rendered_html=rendered_html,
        output_path=output_path,
        template_name=template_name,
        from_cache=from_cache,
    )

    if site is not None:
        set_page_site(page, site)
    if section is not None:
        set_page_section(page, section)

    return cast("PageLike", page)
