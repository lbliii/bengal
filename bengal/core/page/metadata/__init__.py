"""
Page metadata package - mixins for metadata, visibility, URLs, and type checking.

PageMetadataMixin is composed from:
- base: metadata, frontmatter, is_virtual, template_name, prerendered_html, relative_path
- titles: title, nav_title, weight, date, version, slug
- urls: href, _path, absolute_href, _fallback_url
- type_check: toc_items, is_generated, is_home, is_section, is_page, kind
- component: type, description, variant, props, params, draft, keywords
- visibility: visibility, in_listings, in_sitemap, in_search, in_rss, etc.
- helpers: hidden, edition, in_variant, get_user_metadata, get_internal_metadata
- internal: is_autodoc, tag_slug, internal_posts, internal_section, etc.
"""

from __future__ import annotations

from .base import PageMetadataBaseMixin
from .component import PageMetadataComponentMixin
from .helpers import PageMetadataHelpersMixin
from .internal import PageMetadataInternalMixin
from .titles import PageMetadataTitlesMixin
from .type_check import PageMetadataTypeCheckMixin
from .urls import PageMetadataUrlsMixin
from .visibility import PageMetadataVisibilityMixin


class PageMetadataMixin(
    PageMetadataBaseMixin,
    PageMetadataTitlesMixin,
    PageMetadataUrlsMixin,
    PageMetadataTypeCheckMixin,
    PageMetadataComponentMixin,
    PageMetadataVisibilityMixin,
    PageMetadataHelpersMixin,
    PageMetadataInternalMixin,
):
    """
    Mixin providing metadata properties and type checking for pages.

    Composed from sub-mixins for maintainability. See package docstring.
    """
