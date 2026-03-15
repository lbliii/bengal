"""
Page metadata URLs mixin - href, _path, absolute_href.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.utils.url import apply_baseurl, get_baseurl, get_site_origin

if TYPE_CHECKING:
    from bengal.core.site import Site


class PageMetadataUrlsMixin:
    """URL properties: href, _path, absolute_href."""

    output_path: object  # Path | None
    _site: Site | None
    metadata: object
    source_path: object

    def _fallback_url(self) -> str:
        """
        Generate fallback URL when output_path or site not available.

        Used during page construction before output_path is determined.
        """
        return f"/{self.slug}/"

    @property
    def _path(self) -> str:
        """Internal site-relative path. NO baseurl.

        Cost: O(1) cached — cached via _path_cache after first computation.
        First access: O(n) pathlib.relative_to if output_path is set.

        NEVER use in templates — use .href instead.
        """
        manual_value = self.__dict__.get("_path")
        if manual_value is not None:
            return manual_value

        cached = self.__dict__.get("_path_cache")
        if cached is not None:
            return cached

        if not self.output_path:
            return self._fallback_url()

        if not self._site:
            return self._fallback_url()

        try:
            rel_path = self.output_path.relative_to(self._site.output_dir)
        except ValueError:
            emit_diagnostic(
                self,
                "debug",
                "page_output_path_fallback",
                output_path=str(self.output_path),
                output_dir=str(self._site.output_dir),
                page_source=str(getattr(self, "source_path", "unknown")),
            )
            return self._fallback_url()

        url_parts = list(rel_path.parts)
        if url_parts and url_parts[-1] == "index.html":
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith(".html"):
            url_parts[-1] = url_parts[-1][:-5]

        if not url_parts:
            url = "/"
        else:
            url = "/" + "/".join(url_parts)
            if not url.endswith("/"):
                url += "/"

        self.__dict__["_path_cache"] = url
        return url

    @property
    def href(self) -> str:
        """URL for template href attributes. Includes baseurl.

        Cost: O(1) cached — cached after first computation via _href_cache.

        Hot-path alternative: page.identity.href (pre-computed, no property chain).
        """
        manual_value = self.__dict__.get("href")
        if manual_value is not None:
            return manual_value

        cached = self.__dict__.get("_href_cache")
        if cached is not None:
            return cached

        rel = self._path or "/"

        try:
            site = getattr(self, "_site", None)
            baseurl = get_baseurl(site) if site else ""
        except Exception as e:
            emit_diagnostic(self, "debug", "page_baseurl_lookup_failed", error=str(e))
            baseurl = ""

        result = apply_baseurl(rel, baseurl)

        if "_path_cache" in self.__dict__:
            self.__dict__["_href_cache"] = result

        return result

    @property
    def absolute_href(self) -> str:
        """Fully-qualified URL for meta tags and sitemaps when available.

        Cost: O(1) cached — delegates to cached href / _path.
        """
        origin = get_site_origin(self._site) if self._site else ""
        if not origin:
            return self.href
        return f"{origin}{self._path}"
