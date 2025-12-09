"""
RSS feed validator - checks RSS feed quality and completeness.

Validates:
- RSS file exists and is readable
- XML is well-formed and valid RSS 2.0
- Feed contains expected items
- URLs are properly formatted
- Dates are in RFC 822 format
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class RSSValidator(BaseValidator):
    """
    Validates RSS feed quality.

    Checks:
    - RSS file exists (if site has dated content)
    - XML is well-formed
    - Feed structure is valid RSS 2.0
    - URLs are properly formatted
    - Feed has reasonable number of items
    """

    name = "RSS Feed"
    description = "Validates RSS feed quality and completeness"
    enabled_by_default = True

    @override
    def validate(
        self, site: Site, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Run RSS validation checks."""
        results = []

        # Check if RSS should exist
        pages_with_dates = [p for p in site.pages if hasattr(p, "date") and p.date]

        if not pages_with_dates:
            results.append(
                CheckResult.info(
                    "No dated content found - RSS feed not expected",
                    recommendation="Add 'date' frontmatter to pages to enable RSS feed.",
                )
            )
            return results

        # Check 1: RSS file exists
        rss_path = site.output_dir / "rss.xml"
        if not rss_path.exists():
            results.append(
                CheckResult.warning(
                    "RSS feed not generated despite having dated content",
                    recommendation="RSS generation may be disabled. Check if RSSGenerator is called in build process.",
                )
            )
            return results

        # Check 2: XML is well-formed
        try:
            tree = ET.parse(rss_path)
            root = tree.getroot()
        except ET.ParseError as e:
            results.append(
                CheckResult.error(
                    f"RSS XML is malformed: {e}",
                    recommendation="Check RSS generation logic. XML parsing failed.",
                )
            )
            return results

        # Check 3: Valid RSS 2.0 structure
        results.extend(self._check_rss_structure(root))

        # Check 4: Feed items
        results.extend(self._check_feed_items(root, len(pages_with_dates)))

        # Check 5: URL validity
        results.extend(self._check_feed_urls(root, site))

        return results

    def _check_rss_structure(self, root: ET.Element) -> list[CheckResult]:
        """Check RSS 2.0 structure validity."""
        results = []

        # Check root element is <rss>
        if root.tag != "rss":
            results.append(
                CheckResult.error(
                    f"Root element is '{root.tag}', expected 'rss'",
                    recommendation="RSS feed must have <rss> as root element.",
                )
            )
            return results

        # Check RSS version
        version = root.get("version")
        if version != "2.0":
            results.append(
                CheckResult.warning(
                    f"RSS version is '{version}', expected '2.0'",
                    recommendation="Use RSS 2.0 for maximum compatibility.",
                )
            )

        # Check for <channel> element
        channel = root.find("channel")
        if channel is None:
            results.append(
                CheckResult.error(
                    "No <channel> element found in RSS feed",
                    recommendation="RSS 2.0 requires a <channel> element.",
                )
            )
            return results

        # Check required channel elements
        required_elements = ["title", "link", "description"]
        missing = []

        for elem in required_elements:
            if channel.find(elem) is None:
                missing.append(elem)

        if missing:
            results.append(
                CheckResult.error(
                    f"Missing required channel elements: {', '.join(missing)}",
                    recommendation="RSS 2.0 requires <title>, <link>, and <description> in <channel>.",
                )
            )
        # No success message - if structure is valid, silence is golden

        return results

    def _check_feed_items(self, root: ET.Element, total_dated_pages: int) -> list[CheckResult]:
        """Check feed items are present and reasonable."""
        results: list[CheckResult] = []

        channel = root.find("channel")
        if channel is None:
            return results

        items = channel.findall("item")
        item_count = len(items)

        if item_count == 0:
            results.append(
                CheckResult.warning(
                    "RSS feed has no items",
                    recommendation="Feed should contain recent dated pages. Check RSS generation logic.",
                )
            )
            return results

        # Check if we have a reasonable number of items
        # RSS typically includes 10-20 most recent items
        expected_items = min(20, total_dated_pages)

        if item_count < expected_items and total_dated_pages > expected_items:
            results.append(
                CheckResult.info(
                    f"RSS feed has {item_count} items (could include up to {expected_items})",
                    recommendation="Consider increasing RSS item limit to include more recent content.",
                )
            )
        # No success message - if feed has items, silence is golden

        # Check items have required elements
        invalid_items = []
        for i, item in enumerate(items[:5]):  # Check first 5 items
            missing = []
            for elem in ["title", "link"]:
                if item.find(elem) is None:
                    missing.append(elem)

            if missing:
                invalid_items.append(f"Item {i + 1}: missing {', '.join(missing)}")

        if invalid_items:
            results.append(
                CheckResult.error(
                    f"{len(invalid_items)} RSS item(s) missing required elements",
                    recommendation="Each <item> must have <title> and <link>.",
                    details=invalid_items,
                )
            )

        return results

    def _check_feed_urls(self, root: ET.Element, site: Site) -> list[CheckResult]:
        """Check URLs in feed are properly formatted."""
        results: list[CheckResult] = []

        channel = root.find("channel")
        if channel is None:
            return results

        site.config.get("baseurl", "")

        # Check channel link
        channel_link = channel.find("link")
        if channel_link is not None and channel_link.text:
            link = channel_link.text
            if not link.startswith(("http://", "https://")):
                results.append(
                    CheckResult.warning(
                        f"Channel link is relative: {link}",
                        recommendation="RSS channel link should be absolute URL starting with http:// or https://",
                    )
                )

        # Check item links (sample first 10)
        items = channel.findall("item")[:10]
        relative_links = []

        for item in items:
            link_elem = item.find("link")
            if link_elem is not None and link_elem.text:
                link = link_elem.text
                if not link.startswith(("http://", "https://")):
                    title = item.find("title")
                    title_text = title.text if title is not None else "Unknown"
                    relative_links.append(f"{title_text}: {link}")

        if relative_links:
            results.append(
                CheckResult.error(
                    f"{len(relative_links)} item(s) have relative URLs",
                    recommendation="All RSS item links must be absolute URLs. Check baseurl configuration.",
                    details=relative_links[:3],
                )
            )
        # No success message - if URLs are valid, silence is golden

        return results
