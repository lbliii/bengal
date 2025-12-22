"""
Font management for Bengal SSG.

This package provides automatic font downloading and CSS generation for
self-hosted Google Fonts. It enables sites to serve fonts locally without
external requests, improving privacy and performance.

Components:
    FontHelper: Main interface for processing font configuration
    GoogleFontsDownloader: Downloads .woff2 files from Google Fonts API
    FontCSSGenerator: Generates @font-face CSS with CSS custom properties
    FontVariant: Data class representing a specific font weight/style

Workflow:
    1. Parse [fonts] configuration from bengal.toml
    2. Download font files via Google Fonts CSS API
    3. Generate fonts.css with @font-face rules
    4. Optionally rewrite URLs for fingerprinted assets

Configuration:
    Fonts are configured in bengal.toml using simple string or dict format:

    ```toml
    [fonts]
    # Simple format: "family:weight1,weight2,..."
    primary = "Inter:400,600,700"
    heading = "Playfair Display:700"

    # Detailed format with italic support
    [fonts.body]
    family = "Source Sans Pro"
    weights = [400, 600]
    styles = ["normal", "italic"]
    ```

Output:
    - Font files: assets/fonts/{family}-{weight}.woff2
    - CSS file: assets/fonts.css (with @font-face rules and CSS variables)

Example:
    >>> from bengal.fonts import FontHelper
    >>> helper = FontHelper({"primary": "Inter:400,700"})
    >>> css_path = helper.process(Path("output/assets"))
    >>> print(css_path)
    output/assets/fonts.css

Related:
    - bengal/orchestration/asset_orchestrator.py: Asset processing integration
    - bengal/postprocess/fingerprint.py: URL rewriting for fingerprinted fonts
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bengal.fonts.downloader import FontVariant, GoogleFontsDownloader
from bengal.fonts.generator import FontCSSGenerator


def rewrite_font_urls_with_fingerprints(
    fonts_css_path: Path, asset_manifest: dict[str, Any]
) -> bool:
    """
    Rewrite font URLs in fonts.css to use fingerprinted filenames.

    After asset fingerprinting, font files have content-hashed names for
    cache busting (e.g., ``fonts/outfit-400.6c18d579.woff2``). This function
    updates the generated fonts.css to reference these fingerprinted names
    instead of the original filenames.

    Args:
        fonts_css_path: Absolute path to fonts.css in output directory.
        asset_manifest: Asset manifest dict with 'assets' key mapping
            logical paths to fingerprinted output paths. Expected structure::

                {
                    "assets": {
                        "fonts/outfit-400.woff2": {
                            "output_path": "assets/fonts/outfit-400.6c18d579.woff2"
                        }
                    }
                }

    Returns:
        True if fonts.css was modified, False if no changes were needed
        (file doesn't exist, no font assets in manifest, or URLs already match).

    Example:
        >>> manifest = {"assets": {"fonts/inter-400.woff2": {"output_path": "assets/fonts/inter-400.abc123.woff2"}}}
        >>> updated = rewrite_font_urls_with_fingerprints(Path("public/assets/fonts.css"), manifest)
        >>> print(updated)
        True
    """
    if not fonts_css_path.exists():
        return False

    assets = asset_manifest.get("assets", {})
    if not assets:
        return False

    css_content = fonts_css_path.read_text(encoding="utf-8")
    original_content = css_content

    # Build a mapping of original font filenames to fingerprinted filenames
    # Asset manifest has entries like: "fonts/outfit-400.woff2" -> {"output_path": "assets/fonts/outfit-400.6c18d579.woff2"}
    for logical_path, entry in assets.items():
        if not logical_path.startswith("fonts/") or not logical_path.endswith(".woff2"):
            continue

        output_path = entry.get("output_path", "")
        if not output_path:
            continue

        # Extract filenames
        # logical_path: "fonts/outfit-400.woff2"
        # output_path: "assets/fonts/outfit-400.6c18d579.woff2"
        original_filename = Path(logical_path).name  # outfit-400.woff2
        fingerprinted_filename = Path(output_path).name  # outfit-400.6c18d579.woff2

        if original_filename != fingerprinted_filename:
            # Replace in CSS: url('fonts/outfit-400.woff2') -> url('fonts/outfit-400.6c18d579.woff2')
            # Use regex to handle both single and double quotes
            pattern = rf"url\(['\"]?fonts/{re.escape(original_filename)}['\"]?\)"
            replacement = f"url('fonts/{fingerprinted_filename}')"
            css_content = re.sub(pattern, replacement, css_content)

    if css_content != original_content:
        fonts_css_path.write_text(css_content, encoding="utf-8")
        return True

    return False


class FontHelper:
    """
    Main interface for font processing in Bengal.

    Coordinates font downloading and CSS generation based on the ``[fonts]``
    configuration section in bengal.toml. Handles caching to avoid redundant
    downloads and writes.

    Attributes:
        config: Font configuration dictionary from bengal.toml.
        downloader: GoogleFontsDownloader instance for fetching font files.
        generator: FontCSSGenerator instance for creating @font-face CSS.

    Example:
        >>> config = {
        ...     "primary": "Inter:400,600,700",
        ...     "heading": "Playfair Display:700"
        ... }
        >>> helper = FontHelper(config)
        >>> css_path = helper.process(Path("output/assets"))
        >>> print(css_path)
        output/assets/fonts.css

    See Also:
        GoogleFontsDownloader: Font file downloading.
        FontCSSGenerator: CSS generation.
    """

    def __init__(self, font_config: dict[str, Any]) -> None:
        """
        Initialize the font helper with configuration.

        Args:
            font_config: The ``[fonts]`` section from bengal.toml. Keys are
                font role names (e.g., "primary", "heading"), values are either
                simple strings (``"Inter:400,700"``) or dicts with ``family``,
                ``weights``, and ``styles`` keys.
        """
        self.config = font_config
        self.downloader = GoogleFontsDownloader()
        self.generator = FontCSSGenerator()

    def process(self, assets_dir: Path) -> Path | None:
        """
        Download font files and generate fonts.css.

        Parses the font configuration, downloads any missing font files from
        Google Fonts, and generates a fonts.css file with @font-face rules
        and CSS custom properties.

        Font files are cached—existing files are not re-downloaded. The CSS
        file is only written if its content has changed, preventing file
        watcher loops during development.

        Args:
            assets_dir: Absolute path to the assets directory. Font files
                will be placed in ``assets_dir/fonts/`` and fonts.css will
                be written to ``assets_dir/fonts.css``.

        Returns:
            Path to the generated fonts.css file, or None if no fonts are
            configured or all font downloads failed.

        Example:
            >>> helper = FontHelper({"primary": "Inter:400,700"})
            >>> css_path = helper.process(Path("/project/public/assets"))
            >>> print(css_path)
            /project/public/assets/fonts.css
        """
        if not self.config:
            return None

        # Parse config
        fonts_to_download = self._parse_config()

        if not fonts_to_download:
            return None

        from bengal.output import CLIOutput

        cli = CLIOutput()
        cli.section("Fonts")

        # Download fonts
        fonts_dir = assets_dir / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)

        all_variants = {}
        for font_name, font_spec in fonts_to_download.items():
            cli.detail(f"{font_spec['family']}...", indent=1)
            variants = self.downloader.download_font(
                family=font_spec["family"],
                weights=font_spec["weights"],
                styles=font_spec.get("styles", ["normal"]),
                output_dir=fonts_dir,
            )
            all_variants[font_name] = variants

        # Generate CSS
        css_content = self.generator.generate(all_variants)

        if not css_content:
            cli.detail("No fonts generated", indent=1, icon=cli.icons.tree_end)
            return None

        css_path = assets_dir / "fonts.css"
        total_variants = sum(len(v) for v in all_variants.values())

        # Only write if content has changed (prevents file watcher loops)
        if css_path.exists():
            existing_content = css_path.read_text(encoding="utf-8")
            if existing_content == css_content:
                cli.detail(
                    f"Cached: fonts.css ({total_variants} variants)",
                    indent=1,
                    icon=cli.icons.tree_end,
                )
                return css_path

        css_path.write_text(css_content, encoding="utf-8")
        cli.detail(
            f"Generated: fonts.css ({total_variants} variants)", indent=1, icon=cli.icons.tree_end
        )

        return css_path

    def _parse_config(self) -> dict[str, dict[str, Any]]:
        """
        Parse font configuration into a normalized internal format.

        Supports two configuration formats:

        1. **Simple string**: ``"FamilyName:weight1,weight2"``
           Example: ``"Inter:400,600,700"``

        2. **Detailed dict**: ``{family = "...", weights = [...], styles = [...]}``
           Example::

               [fonts.body]
               family = "Source Sans Pro"
               weights = [400, 600]
               styles = ["normal", "italic"]

        Returns:
            Dictionary mapping font role names to normalized specifications::

                {
                    "primary": {
                        "family": "Inter",
                        "weights": [400, 600, 700],
                        "styles": ["normal"]
                    }
                }
        """
        fonts = {}

        for key, value in self.config.items():
            # Skip config keys
            if key == "config":
                continue

            # Parse different config formats
            if isinstance(value, str):
                # Simple string: "Inter:400,600,700"
                if ":" in value:
                    family, weights_str = value.split(":", 1)
                    weights = [int(w.strip()) for w in weights_str.split(",")]
                else:
                    family = value
                    weights = [400]  # Default weight

                fonts[key] = {
                    "family": family,
                    "weights": weights,
                    "styles": ["normal"],
                }

            elif isinstance(value, dict):
                # Detailed dict format
                fonts[key] = {
                    "family": value["family"],
                    "weights": value.get("weights", [400]),
                    "styles": value.get("styles", ["normal"]),
                }

        return fonts


__all__ = [
    "FontCSSGenerator",
    "FontHelper",
    "FontVariant",
    "GoogleFontsDownloader",
    "rewrite_font_urls_with_fingerprints",
]
