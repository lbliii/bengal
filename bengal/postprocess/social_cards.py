"""
Social card (Open Graph image) generation for Bengal SSG.

Automatically generates branded preview images for social media sharing.
When documentation links are shared on Twitter, Slack, Discord, or other
platforms, users see beautiful cards with page title, description, and
site branding.

Key Concepts:
- Social cards: 1200x630px PNG images for Open Graph
- Templates: Default (branded), minimal (centered), documentation (badges)
- Caching: Content-based hash prevents unnecessary regeneration
- Sequential generation: Required for Pillow thread-safety

Configuration:
Social cards are configured in bengal.toml:

    ```toml
    [social_cards]
    enabled = true
    template = "default"  # default, minimal, documentation
    background_color = "#1a1a2e"
    text_color = "#ffffff"
    accent_color = "#4f46e5"
    ```

Related Modules:
- bengal.orchestration.postprocess: Post-processing orchestration
- bengal.rendering.template_functions.seo: OG image injection
- bengal.fonts: Font loading infrastructure

See Also:
- plan/drafted/rfc-social-cards.md: Design documentation

Thread Safety Note:
Pillow's C extensions are NOT thread-safe in free-threading Python (3.13+).
Social card generation uses sequential mode to avoid segfaults.
This is acceptable since social cards are only generated for production
builds, not during dev server operation.

"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageFont

from bengal.utils.observability.logger import get_logger
from bengal.utils.paths.url_normalization import path_to_slug

if TYPE_CHECKING:
    from bengal.config.accessor import Config
    from bengal.core.output import OutputCollector
    from bengal.protocols import PageLike, SiteLike

logger = get_logger(__name__)

# Standard OG image dimensions
CARD_WIDTH = 1200
CARD_HEIGHT = 630


# Check if running in free-threading (no-GIL) mode
# Pillow's C extensions are NOT thread-safe without the GIL
def _is_free_threading() -> bool:
    """Check if running in Python's free-threading (no-GIL) mode."""
    return hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled()


@dataclass
class SocialCardConfig:
    """
    Configuration for social card generation.

    Attributes:
        enabled: Whether social cards are enabled
        template: Template style (default, minimal, documentation)
        background_color: Card background color (hex)
        text_color: Primary text color (hex)
        accent_color: Accent color for decorations (hex)
        title_font: Font for title text
        body_font: Font for description text
        logo: Optional path to site logo
        show_site_name: Whether to show site name on card
        output_dir: Output directory relative to public/
        format: Image format (png or jpg)
        quality: JPEG quality (1-100)
        cache: Whether to cache generated cards

    """

    enabled: bool = False  # Disabled by default (Pillow not thread-safe in free-threading Python)
    template: str = "default"
    background_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    accent_color: str = "#4f46e5"
    secondary_color: str = "#a0aec0"
    title_font: str = "Inter-Bold"
    body_font: str = "Inter-Regular"
    logo: str | None = None
    show_site_name: bool = True
    output_dir: str = "assets/social"
    format: str = "png"
    quality: int = 90
    cache: bool = True


def parse_social_cards_config(config: Config | dict[str, Any]) -> SocialCardConfig:
    """
    Parse [social_cards] section from bengal.toml.

    Args:
        config: Full site configuration dictionary

    Returns:
        SocialCardConfig with parsed values or defaults

    Example:
            >>> config = {"social_cards": {"enabled": True, "template": "minimal"}}
            >>> sc_config = parse_social_cards_config(config)
            >>> sc_config.template
            'minimal'

    """
    social_config = config.get("social_cards", {})

    # Handle boolean shorthand: social_cards = false
    if isinstance(social_config, bool):
        return SocialCardConfig(enabled=social_config)

    return SocialCardConfig(
        enabled=social_config.get("enabled", True),
        template=social_config.get("template", "default"),
        background_color=social_config.get("background_color", "#1a1a2e"),
        text_color=social_config.get("text_color", "#ffffff"),
        accent_color=social_config.get("accent_color", "#4f46e5"),
        secondary_color=social_config.get("secondary_color", "#a0aec0"),
        title_font=social_config.get("title_font", "Inter-Bold"),
        body_font=social_config.get("body_font", "Inter-Regular"),
        logo=social_config.get("logo"),
        show_site_name=social_config.get("show_site_name", True),
        output_dir=social_config.get("output_dir", "assets/social"),
        format=social_config.get("format", "png"),
        quality=social_config.get("quality", 90),
        cache=social_config.get("cache", True),
    )


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#ffffff" or "ffffff")

    Returns:
        RGB tuple (r, g, b)

    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


class SocialCardGenerator:
    """
    Generates social card (Open Graph) images for pages.

    Creates 1200x630px PNG images with page title, description, and site
    branding for social media preview cards. Supports multiple templates
    and content-based caching.

    Creation:
        Direct instantiation: SocialCardGenerator(site, config)
            - Created by PostprocessOrchestrator for card generation
            - Requires Site instance with rendered pages

    Attributes:
        site: Site instance with pages and configuration
        config: SocialCardConfig with styling options
        _cache: Hash cache for incremental generation
        _cache_lock: Thread-safe cache access

    Relationships:
        - Used by: PostprocessOrchestrator for post-processing phase
        - Uses: Site for page access and configuration
        - Uses: Pillow for image generation

    Thread Safety:
        Uses sequential generation for Pillow thread-safety.
        Font loading is cached for performance.

    Examples:
        generator = SocialCardGenerator(site, config)
        count = generator.generate_all(site.pages, output_dir)

    """

    def __init__(
        self,
        site: SiteLike,
        config: SocialCardConfig,
        collector: OutputCollector | None = None,
    ) -> None:
        """
        Initialize social card generator.

        Args:
            site: Site instance with pages and configuration
            config: SocialCardConfig with styling options
            collector: Optional output collector for hot reload tracking
        """
        self.site = site
        self.config = config
        self._collector = collector
        self._cache: dict[str, str] = {}
        self._cache_lock = Lock()
        self._title_font: ImageFont.FreeTypeFont | None = None
        self._body_font: ImageFont.FreeTypeFont | None = None
        self._small_font: ImageFont.FreeTypeFont | None = None
        self._fonts_available: bool = True  # Assume available until proven otherwise

    def _load_fonts(self) -> bool:
        """
        Load fonts for card rendering (cached).

        Attempts to load fonts in the following order:
        1. Explicitly configured title_font/body_font in social_cards config
        2. Site's configured fonts from [fonts] section (downloads TTF if needed)
        3. Fails gracefully if no fonts available

        Returns:
            True if fonts loaded successfully, False if unavailable.
            When False, social card generation should be skipped.

        Note:
            Font loading is done once and cached for the lifetime of the generator.
            This is a significant optimization for large sites with many pages.
        """
        # Already loaded successfully
        if self._title_font is not None:
            return True

        # Previously failed to load - don't retry
        if not self._fonts_available:
            return False

        try:
            # Try to find and load fonts
            title_path = self._get_font_path(self.config.title_font, bold=True)
            body_path = self._get_font_path(self.config.body_font, bold=False)

            # Load fonts once - these will be reused for all cards
            self._title_font = ImageFont.truetype(str(title_path), 56)
            self._body_font = ImageFont.truetype(str(body_path), 28)
            self._small_font = ImageFont.truetype(str(body_path), 22)

            logger.info(
                "social_cards_fonts_loaded",
                title_font=title_path.name,
                body_font=body_path.name,
            )
            return True

        except OSError as e:
            # Font not available - skip social card generation
            # Don't use load_default() as it causes segfaults with getbbox()
            logger.warning(
                "social_cards_fonts_unavailable",
                requested_font=self.config.title_font,
                error=str(e),
                error_type=type(e).__name__,
                action="skipping_social_cards",
                suggestion="Configure [fonts] section in bengal.toml with Google Font families, or install Inter font locally.",
            )
            self._fonts_available = False
            return False

    def _get_font_path(self, font_name: str, bold: bool = False) -> Path:
        """
        Get path to font file, downloading TTF from Google Fonts if needed.

        Search order:
        1. Explicitly named font (e.g., "Inter-Bold") in site assets
        2. Site's configured fonts (e.g., "Outfit:700") - downloads TTF if needed
        3. Common variations of the font name

        Args:
            font_name: Font name (e.g., "Inter-Bold" or "Outfit")
            bold: Whether to prefer bold weight (700) over regular (400)

        Returns:
            Path to font file

        Raises:
            OSError: If font file not found and cannot be downloaded
        """
        # Check site's fonts directory for existing TTF
        fonts_dir = self.site.root_path / "assets" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)

        # Try exact match first
        for pattern in [f"{font_name}.ttf", f"{font_name.lower()}.ttf"]:
            font_path = fonts_dir / pattern
            if font_path.exists():
                return font_path

        # Try to use site's configured fonts and download TTF version
        site_fonts = self.site.config.get("fonts", {})
        if site_fonts:
            downloaded_path = self._download_site_font_as_ttf(site_fonts, fonts_dir, bold)
            if downloaded_path:
                return downloaded_path

        # Try common font file name patterns (family-weight format)
        weight = 700 if bold else 400
        for family in [
            font_name,
            font_name.replace("-Bold", ""),
            font_name.replace("-Regular", ""),
        ]:
            safe_name = family.lower().replace(" ", "-")
            for filename in [f"{safe_name}-{weight}.ttf", f"{safe_name}.ttf"]:
                font_path = fonts_dir / filename
                if font_path.exists():
                    return font_path

        # Raise if nothing found
        raise OSError(f"Font not found: {font_name}")

    def _download_site_font_as_ttf(
        self, font_config: dict[str, Any], fonts_dir: Path, bold: bool
    ) -> Path | None:
        """
        Download TTF version of site's configured font for image generation.

        Parses the site's [fonts] configuration and downloads the appropriate
        weight in TTF format (which Pillow needs for image generation).

        Args:
            font_config: The [fonts] section from site config
            fonts_dir: Directory to save downloaded fonts
            bold: Whether to get bold weight (700) or regular (400)

        Returns:
            Path to downloaded TTF file, or None if download fails
        """
        from bengal.fonts.downloader import GoogleFontsDownloader

        # Find first configured font family
        for value in font_config.values():
            if isinstance(value, str):
                # Simple format: "Outfit:400,600,700"
                parts = value.split(":")
                family = parts[0]
                weights = [int(w) for w in parts[1].split(",")] if len(parts) > 1 else [400]
            elif isinstance(value, dict):
                # Detailed format: {family: "Outfit", weights: [400, 700]}
                family = value.get("family", "")
                weights = value.get("weights", [400])
            else:
                continue

            if not family:
                continue

            # Pick appropriate weight
            target_weight = 700 if bold else 400
            if target_weight not in weights:
                # Fall back to available weights
                target_weight = max(weights) if bold else min(weights)

            # Check if already downloaded
            safe_name = family.lower().replace(" ", "-")
            ttf_path = fonts_dir / f"{safe_name}-{target_weight}.ttf"
            if ttf_path.exists():
                return ttf_path

            # Download TTF version
            try:
                downloader = GoogleFontsDownloader()
                variants = downloader.download_ttf_font(
                    family=family,
                    weights=[target_weight],
                    output_dir=fonts_dir,
                )
                if variants:
                    return fonts_dir / variants[0].filename
            except Exception as e:
                logger.debug(
                    "social_cards_ttf_download_failed",
                    family=family,
                    weight=target_weight,
                    error=str(e),
                )
                continue

        return None

    def _compute_card_hash(self, page: PageLike) -> str:
        """
        Compute content hash for cache key.

        Hash includes title, description, and config to detect changes
        that require regeneration.

        Args:
            page: Page to compute hash for

        Returns:
            12-character hash string
        """
        title = page.title or ""
        description = page.description or ""
        config_str = (
            f"{self.config.background_color}|"
            f"{self.config.text_color}|"
            f"{self.config.accent_color}|"
            f"{self.config.template}"
        )
        content = f"{title}|{description}|{config_str}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _should_regenerate(self, page: PageLike, output_path: Path) -> bool:
        """
        Check if card needs regeneration.

        Uses content hash to detect changes. Returns True if output doesn't
        exist or content has changed.

        Args:
            page: Page to check
            output_path: Expected output path

        Returns:
            True if card needs to be generated
        """
        if not self.config.cache:
            return True

        if not output_path.exists():
            return True

        current_hash = self._compute_card_hash(page)
        page_key = str(page.source_path)

        with self._cache_lock:
            cached_hash = self._cache.get(page_key)

        return current_hash != cached_hash

    def _get_output_path(self, page: PageLike, output_dir: Path) -> Path:
        """
        Get output path for a page's social card.

        Uses page URL path to create unique filename.

        Args:
            page: Page to generate card for
            output_dir: Base output directory

        Returns:
            Path for social card image
        """
        # Use page's internal path (_path) to create a clean, unique filename
        # e.g., /docs/about/concepts/ → docs-about-concepts.png
        url_path = getattr(page, "_path", None) or "/"
        # Strip leading/trailing slashes and convert to slug format
        slug = path_to_slug(url_path) or "index"

        ext = "jpg" if self.config.format == "jpg" else "png"
        return output_dir / f"{slug}.{ext}"

    def _wrap_text(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 3
    ) -> list[str]:
        """
        Wrap text to fit within width constraint.

        Args:
            text: Text to wrap
            font: Font for measuring
            max_width: Maximum width in pixels
            max_lines: Maximum number of lines

        Returns:
            List of wrapped lines
        """
        if not text:
            return []

        words = text.split()
        lines: list[str] = []
        current_line: list[str] = []

        for word in words:
            test_line = " ".join([*current_line, word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

                if len(lines) >= max_lines:
                    break

        if current_line and len(lines) < max_lines:
            lines.append(" ".join(current_line))

        # Truncate last line if too many lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                lines[-1] = lines[-1][:50] + "…"

        return lines

    def _render_default_template(
        self,
        title: str,
        description: str,
        site_name: str,
        site_url: str | None = None,
        config: SocialCardConfig | None = None,
    ) -> Image.Image | None:
        """
        Render default branded template.

        Layout (1200x630):
        - Top: Site name with accent bar
        - Center: Large title (wrapped)
        - Bottom: Description and URL

        Args:
            title: Page title
            description: Page description
            site_name: Site name for branding
            site_url: Optional site URL for footer
            config: Optional config override for per-page styling

        Returns:
            Rendered PIL Image, or None if fonts unavailable
        """
        if not self._load_fonts():
            return None
        assert self._title_font is not None
        assert self._body_font is not None
        assert self._small_font is not None

        # Use provided config or fall back to instance config
        cfg = config or self.config
        bg_color = _hex_to_rgb(cfg.background_color)
        text_color = _hex_to_rgb(cfg.text_color)
        accent_color = _hex_to_rgb(cfg.accent_color)
        secondary_color = _hex_to_rgb(cfg.secondary_color)

        img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        # Margins
        margin_x = 80
        margin_y = 60
        content_width = CARD_WIDTH - (margin_x * 2)

        # Accent bar at top
        draw.rectangle([(0, 0), (CARD_WIDTH, 8)], fill=accent_color)

        # Site name (top left)
        if cfg.show_site_name and site_name:
            draw.text(
                (margin_x, margin_y),
                site_name.upper(),
                font=self._small_font,
                fill=secondary_color,
            )

        # Title (center area)
        title_y = 160
        title_lines = self._wrap_text(title, self._title_font, content_width, max_lines=3)
        for i, line in enumerate(title_lines):
            draw.text(
                (margin_x, title_y + i * 70),
                line,
                font=self._title_font,
                fill=text_color,
            )

        # Description (below title)
        if description:
            desc_y = title_y + len(title_lines) * 70 + 40
            desc_lines = self._wrap_text(description, self._body_font, content_width, max_lines=2)
            for i, line in enumerate(desc_lines):
                draw.text(
                    (margin_x, desc_y + i * 40),
                    line,
                    font=self._body_font,
                    fill=secondary_color,
                )

        # Footer with URL
        if site_url:
            footer_y = CARD_HEIGHT - margin_y - 20
            # Accent line above footer
            draw.rectangle(
                [(margin_x, footer_y - 20), (margin_x + 60, footer_y - 18)],
                fill=accent_color,
            )
            draw.text(
                (margin_x, footer_y),
                site_url.replace("https://", "").replace("http://", ""),
                font=self._small_font,
                fill=secondary_color,
            )

        return img

    def _render_minimal_template(
        self,
        title: str,
        description: str,
        site_name: str,
        site_url: str | None = None,
        config: SocialCardConfig | None = None,
    ) -> Image.Image | None:
        """
        Render minimal centered template.

        Layout (1200x630):
        - Center: Large centered title
        - Below: Subtle site name

        Args:
            title: Page title
            description: Page description (unused in minimal)
            site_name: Site name for branding
            site_url: Optional site URL (unused in minimal)
            config: Optional config override for per-page styling

        Returns:
            Rendered PIL Image, or None if fonts unavailable
        """
        if not self._load_fonts():
            return None
        assert self._title_font is not None
        assert self._small_font is not None

        # Use provided config or fall back to instance config
        cfg = config or self.config
        bg_color = _hex_to_rgb(cfg.background_color)
        text_color = _hex_to_rgb(cfg.text_color)
        accent_color = _hex_to_rgb(cfg.accent_color)
        secondary_color = _hex_to_rgb(cfg.secondary_color)

        img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        content_width = CARD_WIDTH - 160

        # Title (centered)
        title_lines = self._wrap_text(title, self._title_font, content_width, max_lines=3)
        total_height = len(title_lines) * 70
        start_y = (CARD_HEIGHT - total_height) // 2 - 30

        for i, line in enumerate(title_lines):
            bbox = self._title_font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            x = (CARD_WIDTH - line_width) // 2
            draw.text((x, start_y + i * 70), line, font=self._title_font, fill=text_color)

        # Accent line
        line_y = start_y + total_height + 30
        draw.rectangle(
            [(CARD_WIDTH // 2 - 40, line_y), (CARD_WIDTH // 2 + 40, line_y + 4)],
            fill=accent_color,
        )

        # Site name (centered below)
        if cfg.show_site_name and site_name:
            bbox = self._small_font.getbbox(site_name)
            name_width = bbox[2] - bbox[0]
            x = (CARD_WIDTH - name_width) // 2
            draw.text(
                (x, line_y + 30),
                site_name,
                font=self._small_font,
                fill=secondary_color,
            )

        return img

    def generate_card(self, page: PageLike, output_path: Path) -> Path | None:
        """
        Generate a single social card for a page.

        Respects frontmatter overrides:
        - `image:` in frontmatter skips generation (uses manual image)
        - `social_card: false` disables generation for that page

        Args:
            page: Page to generate card for
            output_path: Path to write card image

        Returns:
            Path to generated card, or None if skipped

        Raises:
            Exception: If card generation fails
        """
        # Check for manual override
        if page.metadata.get("image"):
            return None

        # Check for explicit disable
        social_card_meta = page.metadata.get("social_card")
        if social_card_meta is False:
            return None

        # Get content
        title = page.title or "Untitled"
        description = page.description or ""
        site_name = self.site.title or ""
        site_url = self.site.baseurl or ""

        # Apply per-page overrides using a local copy to avoid mutating shared config
        # This prevents one page's overrides from affecting subsequent pages
        config = self.config
        if isinstance(social_card_meta, dict):
            from dataclasses import replace

            overrides = {}
            if "background_color" in social_card_meta:
                overrides["background_color"] = social_card_meta["background_color"]
            if "accent_color" in social_card_meta:
                overrides["accent_color"] = social_card_meta["accent_color"]
            if overrides:
                config = replace(self.config, **overrides)

        # Select template (use local config for per-page overrides)
        template = config.template
        if template == "minimal":
            img = self._render_minimal_template(title, description, site_name, site_url, config)
        else:
            img = self._render_default_template(title, description, site_name, site_url, config)

        # Skip if fonts unavailable (img is None)
        if img is None:
            return None

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save image
        if self.config.format == "jpg":
            img.save(output_path, "JPEG", quality=self.config.quality, optimize=True)
        else:
            img.save(output_path, "PNG", optimize=True)

        if self._collector:
            from bengal.core.output import OutputType

            self._collector.record(output_path, OutputType.IMAGE, phase="postprocess")

        # Update cache
        page_key = str(page.source_path)
        current_hash = self._compute_card_hash(page)
        with self._cache_lock:
            self._cache[page_key] = current_hash

        return output_path

    def generate_all(self, pages: list[PageLike], output_dir: Path) -> tuple[int, int]:
        """
        Generate social cards for all pages.

        Uses SEQUENTIAL processing because Pillow is NOT thread-safe
        in free-threading Python. This is acceptable since:
        - Social cards are only generated for production builds
        - Dev server skips social cards entirely
        - ~30ms per card is acceptable for deploy builds

        Args:
            pages: List of pages to generate cards for
            output_dir: Base output directory

        Returns:
            Tuple of (generated_count, cached_count)

        Raises:
            Exception: If critical generation error occurs
        """
        if not self.config.enabled:
            return (0, 0)

        # Filter pages that need generation
        pages_to_generate: list[tuple[PageLike, Path]] = []
        cached_count = 0

        for page in pages:
            # Skip pages with manual images or disabled social cards
            if page.metadata.get("image"):
                continue
            if page.metadata.get("social_card") is False:
                continue

            output_path = self._get_output_path(page, output_dir)

            if self._should_regenerate(page, output_path):
                pages_to_generate.append((page, output_path))
            else:
                cached_count += 1

        if not pages_to_generate:
            return (0, cached_count)

        generated_count = 0
        errors: list[tuple[str, str]] = []

        # IMPORTANT: Pillow's C extensions are NOT thread-safe in free-threading Python.
        # We use sequential generation to avoid segmentation faults.
        # This is acceptable since social cards are only generated for production builds,
        # not during dev server operation (~30ms per card).
        logger.debug(
            "social_cards_sequential_mode",
            reason="pillow_thread_safety",
            pages=len(pages_to_generate),
        )

        # Sequential generation (safe for all Python builds)
        for i, (page, output_path) in enumerate(pages_to_generate):
            try:
                result = self.generate_card(page, output_path)
                if result:
                    generated_count += 1
                # Log progress for large batches
                if len(pages_to_generate) > 100 and (i + 1) % 100 == 0:
                    logger.debug(
                        "social_cards_progress",
                        generated=i + 1,
                        total=len(pages_to_generate),
                    )
            except Exception as e:
                errors.append((str(page.source_path), str(e)))
                logger.warning(
                    "social_card_generation_failed",
                    page=str(page.source_path),
                    error=str(e),
                    error_type=type(e).__name__,
                    suggestion="Check page frontmatter for invalid social_card options or font configuration.",
                )

        if errors:
            logger.warning(
                "social_card_generation_completed_with_errors",
                generated=generated_count,
                cached=cached_count,
                errors=len(errors),
                suggestion="Review failed pages for invalid metadata or missing fonts.",
            )
        else:
            logger.info(
                "social_card_generation_complete",
                generated=generated_count,
                cached=cached_count,
            )

        return (generated_count, cached_count)


def get_social_card_path(page: PageLike, config: SocialCardConfig, base_path: str = "") -> str | None:
    """
    Get the path to a page's generated social card.

    Used by SEO template functions to inject og:image meta tag.

    Args:
        page: Page to get card path for
        config: SocialCardConfig for output directory
        base_path: Base path prefix (e.g., site baseurl)

    Returns:
        Path to social card image, or None if page has manual image or disabled

    """
    # Manual image takes precedence
    if page.metadata.get("image"):
        return None

    # Disabled for this page
    if page.metadata.get("social_card") is False:
        return None

    # Not enabled globally
    if not config.enabled:
        return None

    # Build path using page URL path (same logic as _get_output_path)
    url_path = getattr(page, "_path", None) or "/"
    slug = path_to_slug(url_path) or "index"

    ext = "jpg" if config.format == "jpg" else "png"
    output_dir = config.output_dir.lstrip("/")

    # Build URL path, being careful with double slashes
    base_path = base_path.rstrip("/") if base_path else ""
    return f"{base_path}/{output_dir}/{slug}.{ext}"
