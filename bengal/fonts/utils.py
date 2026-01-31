"""
Font utilities for filename handling, SSL fallback, and error display.

This module extracts common patterns from the fonts package to reduce
code duplication and improve maintainability.

Utilities:
    make_safe_name: Convert font family to filesystem-safe kebab-case
    make_style_suffix: Get filename suffix for font style
    make_font_filename: Generate consistent font filenames
    urlopen_with_ssl_fallback: Fetch URL with macOS SSL certificate fallback
    record_and_display_asset_error: Record and display asset errors to CLI

"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.errors import BengalAssetError


def make_safe_name(family: str) -> str:
    """
    Convert font family to filesystem-safe kebab-case name.

    Args:
        family: Font family name (e.g., "Inter", "Playfair Display").

    Returns:
        Lowercase kebab-case name (e.g., "inter", "playfair-display").

    Example:
        >>> make_safe_name("Playfair Display")
        'playfair-display'
    """
    return family.lower().replace(" ", "-")


def make_style_suffix(style: str) -> str:
    """
    Get filename suffix for font style.

    Args:
        style: Font style ("normal" or "italic").

    Returns:
        Empty string for normal, "-italic" for italic.

    Example:
        >>> make_style_suffix("italic")
        '-italic'
        >>> make_style_suffix("normal")
        ''
    """
    return "-italic" if style == "italic" else ""


def make_font_filename(family: str, weight: int, style: str, ext: str = ".woff2") -> str:
    """
    Generate consistent font filename.

    Args:
        family: Font family name.
        weight: Numeric font weight (100-900).
        style: Font style ("normal" or "italic").
        ext: File extension (default ".woff2").

    Returns:
        Filename in format ``{family}-{weight}[-italic].{ext}``.

    Example:
        >>> make_font_filename("Inter", 700, "normal")
        'inter-700.woff2'
        >>> make_font_filename("Inter", 400, "italic", ".ttf")
        'inter-400-italic.ttf'
    """
    safe_name = make_safe_name(family)
    suffix = make_style_suffix(style)
    return f"{safe_name}-{weight}{suffix}{ext}"


def urlopen_with_ssl_fallback(
    url: str,
    *,
    timeout: int = 10,
    user_agent: str,
    decode: bool = False,
) -> bytes | str:
    """
    Fetch URL with automatic SSL fallback for macOS certificate issues.

    On macOS, the default Python installation may not have access to
    system certificates, causing SSL verification to fail. This function
    automatically retries with an unverified SSL context when this occurs.

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.
        user_agent: User-Agent header value.
        decode: If True, decode response as UTF-8 string.

    Returns:
        Response bytes, or decoded string if decode=True.

    Raises:
        urllib.error.URLError: If the request fails (after SSL fallback attempt).

    Example:
        >>> data = urlopen_with_ssl_fallback(
        ...     "https://example.com",
        ...     user_agent="Mozilla/5.0",
        ...     decode=True
        ... )
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
    except (ssl.SSLError, urllib.error.URLError) as e:
        # macOS certificate issue - retry with unverified context
        if "certificate verify failed" in str(e) or "SSL" in str(e):
            ssl_context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                data = response.read()
        else:
            raise

    return data.decode("utf-8") if decode else data


def record_and_display_asset_error(error: BengalAssetError) -> None:
    """
    Record error to session and display to CLI.

    Combines the common pattern of recording an error for aggregation
    and displaying it to the user via CLI output.

    Args:
        error: The BengalAssetError to record and display.

    Example:
        >>> from bengal.errors import BengalAssetError, ErrorCode
        >>> error = BengalAssetError("Download failed", code=ErrorCode.X008)
        >>> record_and_display_asset_error(error)
    """
    from bengal.errors import record_error
    from bengal.errors.display import display_bengal_error
    from bengal.output import CLIOutput

    record_error(error, file_path=None)
    display_bengal_error(error, CLIOutput())
