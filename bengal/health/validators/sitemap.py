"""
Sitemap validator - checks sitemap.xml validity for SEO.

Validates:
- Sitemap file exists
- XML is well-formed
- No duplicate URLs
- URLs are properly formatted
- Sitemap follows protocol
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class SitemapValidator(BaseValidator):
    """
    Validates sitemap.xml for SEO.

    Checks:
    - Sitemap file exists
    - XML is well-formed
    - Follows sitemap protocol (http://www.sitemaps.org/)
    - No duplicate URLs
    - URLs are absolute and properly formatted
    - Sitemap includes expected pages
    """

    name = "Sitemap"
    description = "Validates sitemap.xml for SEO"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run sitemap validation checks."""
        results = []

        # Check 1: Sitemap file exists
        sitemap_path = site.output_dir / "sitemap.xml"
        if not sitemap_path.exists():
            results.append(
                CheckResult.warning(
                    "Sitemap not generated",
                    recommendation="Sitemap.xml is important for SEO. Check if SitemapGenerator is called in build process.",
                )
            )
            return results

        # Check 2: XML is well-formed
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
        except ET.ParseError as e:
            results.append(
                CheckResult.error(
                    f"Sitemap XML is malformed: {e}",
                    recommendation="Check sitemap generation logic. XML parsing failed.",
                )
            )
            return results

        # Check 3: Valid sitemap structure
        results.extend(self._check_sitemap_structure(root))

        # Check 4: URL validity
        results.extend(self._check_sitemap_urls(root, site))

        # Check 5: Duplicate URLs
        results.extend(self._check_duplicate_urls(root))

        # Check 6: Coverage
        results.extend(self._check_sitemap_coverage(root, site))

        return results

    def _check_sitemap_structure(self, root: ET.Element) -> list[CheckResult]:
        """Check sitemap structure validity."""
        results = []

        # Check root element is <urlset>
        # Strip namespace if present
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag != "urlset":
            results.append(
                CheckResult.error(
                    f"Root element is '{tag}', expected 'urlset'",
                    recommendation="Sitemap must have <urlset> as root element.",
                )
            )
            return results

        # Check for xmlns attribute
        xmlns = root.get("{http://www.w3.org/2000/xmlns/}xmlns") or root.get("xmlns")
        if xmlns != "http://www.sitemaps.org/schemas/sitemap/0.9":
            results.append(
                CheckResult.warning(
                    f"Sitemap xmlns is '{xmlns}', expected 'http://www.sitemaps.org/schemas/sitemap/0.9'",
                    recommendation="Use standard sitemap namespace for maximum compatibility.",
                )
            )

        # No success message - if structure is valid, silence is golden

        return results

    def _check_sitemap_urls(self, root: ET.Element, site: Site) -> list[CheckResult]:
        """Check URLs in sitemap are properly formatted."""
        results = []

        # Find all <url> elements (handle namespace)
        urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        if not urls:
            # Try without namespace
            urls = root.findall(".//url")

        if not urls:
            results.append(
                CheckResult.warning(
                    "Sitemap has no <url> elements",
                    recommendation="Sitemap should contain URLs for all pages.",
                )
            )
            return results

        # Check URL format (sample first 10)
        invalid_urls = []
        relative_urls = []

        for url_elem in urls[:10]:
            loc = url_elem.find(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is None:
                loc = url_elem.find(".//loc")

            if loc is None or not loc.text:
                invalid_urls.append("URL missing <loc> element")
                continue

            url = loc.text.strip()

            # Check if URL is absolute
            if not url.startswith(("http://", "https://")):
                relative_urls.append(url)

        if invalid_urls:
            results.append(
                CheckResult.error(
                    f"{len(invalid_urls)} URL(s) missing <loc> element",
                    recommendation="Each <url> must have a <loc> element with the page URL.",
                    details=invalid_urls[:3],
                )
            )

        if relative_urls:
            results.append(
                CheckResult.error(
                    f"{len(relative_urls)} URL(s) are relative",
                    recommendation="All sitemap URLs must be absolute. Check baseurl configuration.",
                    details=relative_urls[:3],
                )
            )

        # No success message - if URLs are valid, silence is golden

        return results

    def _check_duplicate_urls(self, root: ET.Element) -> list[CheckResult]:
        """Check for duplicate URLs in sitemap."""
        results: list[CheckResult] = []

        # Find all <url> elements
        urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        if not urls:
            urls = root.findall(".//url")

        if not urls:
            return results

        # Collect all URLs
        seen_urls: set[str] = set()
        duplicates = []

        for url_elem in urls:
            loc = url_elem.find(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is None:
                loc = url_elem.find(".//loc")

            if loc is not None and loc.text:
                url = loc.text.strip()
                if url in seen_urls:
                    duplicates.append(url)
                seen_urls.add(url)

        if duplicates:
            results.append(
                CheckResult.error(
                    f"{len(duplicates)} duplicate URL(s) in sitemap",
                    recommendation="Each URL should appear only once. Check sitemap generation logic.",
                    details=list(set(duplicates))[:5],
                )
            )
        # No success message - if no duplicates, silence is golden

        return results

    def _check_sitemap_coverage(self, root: ET.Element, site: Site) -> list[CheckResult]:
        """Check sitemap includes expected pages."""
        results = []

        # Find all <url> elements
        urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        if not urls:
            urls = root.findall(".//url")

        sitemap_count = len(urls)

        # Count non-draft pages
        publishable_pages = [p for p in site.pages if not p.metadata.get("draft", False)]
        total_pages = len(publishable_pages)

        # Calculate coverage
        if total_pages > 0:
            (sitemap_count / total_pages) * 100

            if sitemap_count < total_pages:
                missing = total_pages - sitemap_count
                results.append(
                    CheckResult.warning(
                        f"Sitemap has {sitemap_count} URLs but site has {total_pages} publishable pages ({missing} missing)",
                        recommendation="Ensure all pages are included in sitemap. Check if some pages have output_path issues.",
                    )
                )
            # Extra URLs (sitemap_count > total_pages) is normal - generated pages like tags/archives
            # No success message - if coverage is good, silence is golden

        return results
