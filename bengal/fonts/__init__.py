"""
Font helper for Bengal SSG.

Provides simple font downloading and CSS generation for Google Fonts.

Usage:

```toml
# In bengal.toml:
[fonts]
primary = "Inter:400,600,700"
heading = "Playfair Display:700"

# Bengal automatically downloads fonts and generates CSS
```
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

    After asset fingerprinting, font files have hashed names like:
        fonts/outfit-400.6c18d579.woff2

    This function updates fonts.css to reference these fingerprinted names
    instead of the original names like fonts/outfit-400.woff2.

    Args:
        fonts_css_path: Path to fonts.css in output directory
        asset_manifest: Asset manifest dict with 'assets' key mapping
                       logical paths to fingerprinted output paths

    Returns:
        True if fonts.css was updated, False otherwise
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
    Main font helper interface.

    Usage:
        helper = FontHelper(config)
        helper.process(output_dir)
    """

    def __init__(self, font_config: dict[str, Any]):
        """
        Initialize font helper with configuration.

        Args:
            font_config: [fonts] section from bengal.toml
        """
        self.config = font_config
        self.downloader = GoogleFontsDownloader()
        self.generator = FontCSSGenerator()

    def process(self, assets_dir: Path) -> Path | None:
        """
        Process fonts: download files and generate CSS.

        Args:
            assets_dir: Assets directory (fonts go in assets/fonts/)

        Returns:
            Path to generated fonts.css, or None if no fonts configured
        """
        if not self.config:
            return None

        # Parse config
        fonts_to_download = self._parse_config()

        if not fonts_to_download:
            return None

        print("\n🔤 Fonts:")

        # Download fonts
        fonts_dir = assets_dir / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)

        all_variants = {}
        for font_name, font_spec in fonts_to_download.items():
            print(f"   {font_spec['family']}...")
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
            print("   └─ No fonts generated")
            return None

        css_path = assets_dir / "fonts.css"
        total_variants = sum(len(v) for v in all_variants.values())

        # Only write if content has changed (prevents file watcher loops)
        if css_path.exists():
            existing_content = css_path.read_text(encoding="utf-8")
            if existing_content == css_content:
                print(f"   └─ Cached: fonts.css ({total_variants} variants)")
                return css_path

        css_path.write_text(css_content, encoding="utf-8")
        print(f"   └─ Generated: fonts.css ({total_variants} variants)")

        return css_path

    def _parse_config(self) -> dict[str, dict[str, Any]]:
        """
        Parse [fonts] configuration into normalized format.

        Supports two formats:
        1. Simple string: "Inter:400,600,700"
        2. Detailed dict: {family = "Inter", weights = [400, 600, 700]}

        Returns:
            Dict mapping font name to font specification
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
