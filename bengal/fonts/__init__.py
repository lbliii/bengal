"""
Font helper for Bengal SSG.

Provides simple font downloading and CSS generation for Google Fonts.

Usage:
    # In bengal.toml:
    [fonts]
    primary = "Inter:400,600,700"
    heading = "Playfair Display:700"

    # Bengal automatically downloads fonts and generates CSS
"""


from __future__ import annotations

from pathlib import Path
from typing import Any

from bengal.fonts.downloader import FontVariant, GoogleFontsDownloader
from bengal.fonts.generator import FontCSSGenerator


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
        css_path.write_text(css_content, encoding="utf-8")

        total_variants = sum(len(v) for v in all_variants.values())
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


__all__ = ["FontCSSGenerator", "FontHelper", "FontVariant", "GoogleFontsDownloader"]
