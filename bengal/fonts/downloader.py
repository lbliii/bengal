"""
Google Fonts downloader for self-hosted font files.

Downloads .woff2 font files from Google Fonts using only Python stdlib
(no external HTTP libraries required). Fonts are fetched via the Google
Fonts CSS API, which provides direct URLs to font files.

Key Features:
    - No external dependencies (uses urllib.request)
    - Automatic SSL fallback for macOS certificate issues
    - Atomic file writes to prevent corruption
    - Support for multiple weights and italic styles

Architecture:
    This module is a pure utility—it performs network I/O but does not
    interact with Site or Page models. It is used by FontHelper in the
    package's __init__.py.

Example:
    >>> from bengal.fonts.downloader import GoogleFontsDownloader
    >>> downloader = GoogleFontsDownloader()
    >>> variants = downloader.download_font(
    ...     family="Inter",
    ...     weights=[400, 700],
    ...     output_dir=Path("assets/fonts")
    ... )
    >>> for v in variants:
    ...     print(f"{v.family} {v.weight}: {v.filename}")
    Inter 400: inter-400.woff2
    Inter 700: inter-700.woff2

Related:
    - bengal/fonts/__init__.py: FontHelper integration
    - bengal/fonts/generator.py: CSS generation from variants
"""

from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FontVariant:
    """
    Represents a specific font variant (family + weight + style combination).

    Each FontVariant corresponds to a single downloadable font file from
    Google Fonts. The variant includes all metadata needed to generate
    @font-face CSS rules.

    Attributes:
        family: Font family name as displayed (e.g., "Inter", "Playfair Display").
        weight: Numeric font weight (100-900, typically 400 for regular, 700 for bold).
        style: Font style, either "normal" or "italic".
        url: Direct URL to the font file on Google's CDN (.woff2 or .ttf).

    Example:
        >>> variant = FontVariant("Inter", 400, "normal", "https://fonts.gstatic.com/...")
        >>> print(variant.filename)
        inter-400.woff2
        >>> variant_italic = FontVariant("Inter", 400, "italic", "https://...")
        >>> print(variant_italic.filename)
        inter-400-italic.woff2
    """

    family: str
    weight: int
    style: str
    url: str

    @property
    def filename(self) -> str:
        """
        Generate a filesystem-safe filename for this variant.

        Creates a kebab-case filename combining the family name, weight,
        optional italic suffix, and file extension derived from the URL.

        Returns:
            Filename in format ``{family}-{weight}[-italic].{ext}``.
            Example: ``inter-700.woff2`` or ``playfair-display-400-italic.woff2``.
        """
        style_suffix = "-italic" if self.style == "italic" else ""
        safe_name = self.family.lower().replace(" ", "-")
        # Preserve original file extension from URL
        ext = ".woff2" if ".woff2" in self.url else ".ttf" if ".ttf" in self.url else ".woff2"
        return f"{safe_name}-{self.weight}{style_suffix}{ext}"


class GoogleFontsDownloader:
    """
    Downloads font files from Google Fonts for self-hosting.

    Uses the Google Fonts CSS2 API to discover font file URLs, then downloads
    the actual .woff2 (or .ttf) files. No API key is required—the CSS API is
    public and the User-Agent header determines the returned font format.

    The downloader handles:
        - Building properly formatted CSS API URLs
        - Parsing CSS to extract font file URLs
        - SSL certificate issues on macOS (automatic fallback)
        - Atomic file writes to prevent corruption

    Attributes:
        BASE_URL: Google Fonts CSS2 API endpoint.
        USER_AGENT: Browser user-agent that requests woff2 format.

    Example:
        >>> downloader = GoogleFontsDownloader()
        >>> variants = downloader.download_font(
        ...     family="Inter",
        ...     weights=[400, 600, 700],
        ...     styles=["normal", "italic"],
        ...     output_dir=Path("assets/fonts")
        ... )
        >>> len(variants)
        6

    Note:
        The User-Agent string mimics a modern browser to ensure Google
        returns .woff2 format (the most efficient web font format).
    """

    BASE_URL = "https://fonts.googleapis.com/css2"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def download_font(
        self,
        family: str,
        weights: list[int],
        styles: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> list[FontVariant]:
        """
        Download a font family with specified weights.

        Args:
            family: Font family name (e.g., "Inter", "Roboto")
            weights: List of weights (e.g., [400, 700])
            styles: List of styles (e.g., ["normal", "italic"])
            output_dir: Directory to save font files (required)

        Returns:
            List of downloaded FontVariant objects

        Raises:
            ValueError: If output_dir is not provided

        Note:
            output_dir must be explicit - no fallback to Path.cwd() to ensure
            consistent behavior. See: plan/implemented/rfc-path-resolution-architecture.md
        """
        from bengal.errors import BengalError

        if output_dir is None:
            raise BengalError(
                "output_dir is required for download_font",
                suggestion="Provide an absolute output directory path",
            )
        styles = styles or ["normal"]
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build Google Fonts CSS URL
        css_url = self._build_css_url(family, weights, styles)

        try:
            # Fetch the CSS to get font URLs
            font_urls = self._extract_font_urls(css_url)

            if not font_urls:
                logger.warning("no_fonts_found_for_family", family=family)
                return []

            # Download each font file
            variants = []
            for weight in weights:
                for style in styles:
                    key = f"{weight}-{style}"
                    if key in font_urls:
                        url = font_urls[key]
                        variant = FontVariant(family, weight, style, url)

                        # Download the font file
                        output_path = output_dir / variant.filename
                        if not output_path.exists():
                            self._download_file(url, output_path)
                            from bengal.output import CLIOutput

                            cli = CLIOutput()
                            cli.detail(
                                f"Downloaded: {variant.filename}", indent=2, icon=cli.icons.success
                            )
                        else:
                            from bengal.output import CLIOutput

                            cli = CLIOutput()
                            cli.detail(
                                f"Cached: {variant.filename}", indent=2, icon=cli.icons.success
                            )

                        variants.append(variant)

            return variants

        except Exception as e:
            logger.error(
                "font_download_failed", family=family, error=str(e), error_type=type(e).__name__
            )
            return []

    def _build_css_url(self, family: str, weights: list[int], styles: list[str]) -> str:
        """
        Build a Google Fonts CSS2 API URL for the specified font configuration.

        Constructs the URL according to Google Fonts API format:
            - Normal only: ``family:wght@400;700``
            - With italic: ``family:ital,wght@0,400;1,400;0,700;1,700``

        Args:
            family: Font family name (spaces will be URL-encoded as ``+``).
            weights: List of numeric weights to include.
            styles: List of styles (``"normal"`` and/or ``"italic"``).

        Returns:
            Complete Google Fonts CSS2 API URL with ``display=swap`` parameter.
        """
        family_encoded = family.replace(" ", "+")

        if len(styles) == 1 and styles[0] == "normal":
            # Simple format for normal style only
            weights_str = ";".join(str(w) for w in sorted(weights))
            url = f"{self.BASE_URL}?family={family_encoded}:wght@{weights_str}&display=swap"
        else:
            # Full format with italic support
            specs = []
            for weight in sorted(weights):
                for style in styles:
                    ital = "1" if style == "italic" else "0"
                    specs.append(f"{ital},{weight}")
            specs_str = ";".join(specs)
            url = f"{self.BASE_URL}?family={family_encoded}:ital,wght@{specs_str}&display=swap"

        return url

    def _extract_font_urls(self, css_url: str) -> dict[str, str]:
        """
        Fetch CSS from Google Fonts and extract font file URLs.

        Requests the CSS2 API endpoint, parses the returned @font-face rules,
        and extracts direct URLs to .woff2 or .ttf files.

        Args:
            css_url: Complete Google Fonts CSS2 API URL.

        Returns:
            Dictionary mapping ``"{weight}-{style}"`` keys to font file URLs.
            Example: ``{"400-normal": "https://fonts.gstatic.com/...", ...}``

        Raises:
            urllib.error.URLError: If the network request fails.
            ssl.SSLError: If SSL verification fails (handled with fallback).
        """
        req = urllib.request.Request(css_url, headers={"User-Agent": self.USER_AGENT})

        # Try with standard SSL verification first, fall back to unverified on macOS
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                css_content = response.read().decode("utf-8")
        except (ssl.SSLError, urllib.error.URLError) as e:
            # macOS certificate issue - retry with unverified context
            if "certificate verify failed" in str(e) or "SSL" in str(e):
                ssl_context = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                    css_content = response.read().decode("utf-8")
            else:
                raise

        # Parse CSS to extract URLs
        # Google Fonts CSS has structure like:
        # /* latin */
        # @font-face {
        #   font-family: 'Inter';
        #   font-style: normal;
        #   font-weight: 400;
        #   src: url(https://fonts.gstatic.com/...woff2);
        # }

        font_urls = {}

        # Find all @font-face blocks
        font_face_pattern = r"@font-face\s*{([^}]+)}"
        for match in re.finditer(font_face_pattern, css_content):
            block = match.group(1)

            # Extract weight, style, and URL (support both woff2 and ttf)
            weight_match = re.search(r"font-weight:\s*(\d+)", block)
            style_match = re.search(r"font-style:\s*(\w+)", block)
            url_match = re.search(r"url\(([^)]+\.(woff2|ttf))", block)

            if weight_match and style_match and url_match:
                weight = weight_match.group(1)
                style = style_match.group(1)
                url = url_match.group(1)

                key = f"{weight}-{style}"
                font_urls[key] = url

        return font_urls

    def _download_file(self, url: str, output_path: Path) -> None:
        """
        Download a file from URL and save it atomically.

        Uses atomic write (write to temp file, then rename) to prevent
        corruption if the download is interrupted. Handles SSL certificate
        issues on macOS with automatic fallback to unverified context.

        Args:
            url: Direct URL to the font file.
            output_path: Destination path for the downloaded file.

        Raises:
            urllib.error.URLError: If the download fails after SSL fallback.
            OSError: If the file cannot be written.
        """
        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})

        # Try with standard SSL verification first, fall back to unverified on macOS
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
        except (ssl.SSLError, urllib.error.URLError) as e:
            # macOS certificate issue - retry with unverified context
            if "certificate verify failed" in str(e) or "SSL" in str(e):
                ssl_context = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                    data = response.read()
            else:
                raise

        # Atomic write for safety
        tmp_path = output_path.with_suffix(".tmp")
        try:
            tmp_path.write_bytes(data)
            tmp_path.replace(output_path)
        except Exception as e:
            logger.debug(
                "font_downloader_atomic_write_failed",
                output_path=str(output_path),
                error=str(e),
                error_type=type(e).__name__,
                action="cleaning_up_temp_file",
            )
            tmp_path.unlink(missing_ok=True)
            raise
