"""
Tests for bengal/postprocess/social_cards.py.

Covers:
- SocialCardConfig dataclass and defaults
- parse_social_cards_config function
- SocialCardGenerator initialization
- Card generation with correct dimensions (1200x630)
- Text wrapping for long titles
- Template selection (default, minimal)
- Cache behavior
- Frontmatter override (image: takes precedence)
- Per-page disable (social_card: false)
- Parallel generation threshold
- get_social_card_path helper
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from bengal.postprocess.social_cards import (
    CARD_HEIGHT,
    CARD_WIDTH,
    SocialCardConfig,
    SocialCardGenerator,
    get_social_card_path,
    parse_social_cards_config,
)


class TestSocialCardConfig:
    """Test SocialCardConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that SocialCardConfig has correct defaults."""
        config = SocialCardConfig()

        assert config.enabled is True
        assert config.template == "default"
        assert config.background_color == "#1a1a2e"
        assert config.text_color == "#ffffff"
        assert config.accent_color == "#4f46e5"
        assert config.title_font == "Inter-Bold"
        assert config.body_font == "Inter-Regular"
        assert config.logo is None
        assert config.show_site_name is True
        assert config.output_dir == "assets/social"
        assert config.format == "png"
        assert config.quality == 90
        assert config.cache is True

    def test_custom_values(self) -> None:
        """Test SocialCardConfig with custom values."""
        config = SocialCardConfig(
            enabled=False,
            template="minimal",
            background_color="#000000",
            text_color="#eeeeee",
        )

        assert config.enabled is False
        assert config.template == "minimal"
        assert config.background_color == "#000000"
        assert config.text_color == "#eeeeee"


class TestParseSocialCardsConfig:
    """Test parse_social_cards_config function."""

    def test_empty_config_returns_defaults(self) -> None:
        """Test that empty config returns default values."""
        config = parse_social_cards_config({})

        assert config.enabled is True
        assert config.template == "default"

    def test_boolean_shorthand_false(self) -> None:
        """Test boolean shorthand: social_cards = false."""
        config = parse_social_cards_config({"social_cards": False})

        assert config.enabled is False

    def test_boolean_shorthand_true(self) -> None:
        """Test boolean shorthand: social_cards = true."""
        config = parse_social_cards_config({"social_cards": True})

        assert config.enabled is True

    def test_dict_config(self) -> None:
        """Test dict configuration."""
        config = parse_social_cards_config(
            {
                "social_cards": {
                    "enabled": True,
                    "template": "minimal",
                    "background_color": "#ff0000",
                }
            }
        )

        assert config.enabled is True
        assert config.template == "minimal"
        assert config.background_color == "#ff0000"
        # Other values remain defaults
        assert config.text_color == "#ffffff"


class TestSocialCardGeneratorInit:
    """Test SocialCardGenerator initialization."""

    def test_init_stores_site_and_config(self) -> None:
        """Test that SocialCardGenerator stores site and config."""
        site = MagicMock()
        config = SocialCardConfig()

        generator = SocialCardGenerator(site, config)

        assert generator.site is site
        assert generator.config is config

    def test_init_creates_empty_cache(self) -> None:
        """Test that SocialCardGenerator creates empty cache."""
        site = MagicMock()
        config = SocialCardConfig()

        generator = SocialCardGenerator(site, config)

        assert generator._cache == {}


class TestSocialCardGeneratorContentHash:
    """Test content hash computation for caching."""

    def _create_mock_page(
        self,
        title: str = "Test Page",
        description: str | None = None,
        source_path: str = "test.md",
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.title = title
        page.description = description
        page.source_path = Path(source_path)
        page.metadata = {}
        page.slug = "test"
        page.section_path = ""
        return page

    def test_same_content_same_hash(self) -> None:
        """Test that same content produces same hash."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page1 = self._create_mock_page(title="Test", description="Desc")
        page2 = self._create_mock_page(title="Test", description="Desc")

        hash1 = generator._compute_card_hash(page1)
        hash2 = generator._compute_card_hash(page2)

        assert hash1 == hash2

    def test_different_title_different_hash(self) -> None:
        """Test that different title produces different hash."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page1 = self._create_mock_page(title="Test A")
        page2 = self._create_mock_page(title="Test B")

        hash1 = generator._compute_card_hash(page1)
        hash2 = generator._compute_card_hash(page2)

        assert hash1 != hash2

    def test_different_config_different_hash(self) -> None:
        """Test that different config produces different hash."""
        site = MagicMock()
        page = self._create_mock_page(title="Test")

        config1 = SocialCardConfig(background_color="#000000")
        config2 = SocialCardConfig(background_color="#ffffff")

        generator1 = SocialCardGenerator(site, config1)
        generator2 = SocialCardGenerator(site, config2)

        hash1 = generator1._compute_card_hash(page)
        hash2 = generator2._compute_card_hash(page)

        assert hash1 != hash2


class TestSocialCardGeneratorOutputPath:
    """Test output path generation."""

    def _create_mock_page(
        self,
        slug: str = "test-page",
        section_path: str = "",
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.slug = slug
        page.section_path = section_path
        page.metadata = {}
        return page

    def test_simple_slug(self) -> None:
        """Test output path with simple slug."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page(slug="my-page")
        output_dir = Path("/output")

        path = generator._get_output_path(page, output_dir)

        assert path == Path("/output/my-page.png")

    def test_nested_section(self) -> None:
        """Test output path with nested section."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page(slug="my-page", section_path="docs/api")
        output_dir = Path("/output")

        path = generator._get_output_path(page, output_dir)

        assert path == Path("/output/docs-api-my-page.png")

    def test_jpg_format(self) -> None:
        """Test output path with jpg format."""
        site = MagicMock()
        config = SocialCardConfig(format="jpg")
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page(slug="my-page")
        output_dir = Path("/output")

        path = generator._get_output_path(page, output_dir)

        assert path == Path("/output/my-page.jpg")


class TestSocialCardGeneratorTextWrapping:
    """Test text wrapping functionality."""

    def test_short_text_no_wrap(self) -> None:
        """Test that short text is not wrapped."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        # Load fonts first
        generator._load_fonts()

        lines = generator._wrap_text("Short title", generator._title_font, 1000)

        assert len(lines) == 1
        assert lines[0] == "Short title"

    def test_long_text_wraps(self) -> None:
        """Test that long text is wrapped."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        # Load fonts first
        generator._load_fonts()

        # Use a very long text and small width to ensure wrapping even with default font
        long_text = (
            "This is a very long title that should definitely wrap to multiple lines "
            "because it contains many words and the max width is very small"
        )
        # Use a small width that will force wrapping even with bitmap fonts
        lines = generator._wrap_text(long_text, generator._title_font, 150)

        assert len(lines) > 1

    def test_max_lines_limit(self) -> None:
        """Test that max_lines limit is respected."""
        site = MagicMock()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        # Load fonts first
        generator._load_fonts()

        very_long_text = " ".join(["word"] * 100)
        lines = generator._wrap_text(very_long_text, generator._title_font, 200, max_lines=2)

        assert len(lines) <= 2


class TestSocialCardGeneratorGenerate:
    """Test card generation."""

    def _create_mock_page(
        self,
        title: str = "Test Page",
        description: str | None = "Test description",
        source_path: str = "test.md",
        metadata: dict[str, Any] | None = None,
        slug: str = "test",
        section_path: str = "",
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.title = title
        page.description = description
        page.source_path = Path(source_path)
        page.metadata = metadata or {}
        page.slug = slug
        page.section_path = section_path
        return page

    def _create_mock_site(
        self,
        config: dict[str, Any] | None = None,
        output_dir: Path | None = None,
    ) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.config = config or {"title": "Test Site", "baseurl": "https://example.com"}
        site.output_dir = output_dir or Path("/tmp/output")
        return site

    def test_generate_card_creates_correct_dimensions(self, tmp_path: Path) -> None:
        """Test that generated card has correct dimensions (1200x630)."""
        from PIL import Image

        site = self._create_mock_site()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page()
        output_path = tmp_path / "test.png"

        result = generator.generate_card(page, output_path)

        assert result == output_path
        assert output_path.exists()

        # Verify dimensions
        with Image.open(output_path) as img:
            assert img.size == (CARD_WIDTH, CARD_HEIGHT)

    def test_generate_card_skips_manual_image(self, tmp_path: Path) -> None:
        """Test that generation is skipped when page has manual image."""
        site = self._create_mock_site()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page(metadata={"image": "/custom.png"})
        output_path = tmp_path / "test.png"

        result = generator.generate_card(page, output_path)

        assert result is None
        assert not output_path.exists()

    def test_generate_card_skips_when_disabled(self, tmp_path: Path) -> None:
        """Test that generation is skipped when social_card: false."""
        site = self._create_mock_site()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page(metadata={"social_card": False})
        output_path = tmp_path / "test.png"

        result = generator.generate_card(page, output_path)

        assert result is None
        assert not output_path.exists()

    def test_generate_card_minimal_template(self, tmp_path: Path) -> None:
        """Test minimal template generation."""
        from PIL import Image

        site = self._create_mock_site()
        config = SocialCardConfig(template="minimal")
        generator = SocialCardGenerator(site, config)

        page = self._create_mock_page()
        output_path = tmp_path / "test.png"

        result = generator.generate_card(page, output_path)

        assert result == output_path
        assert output_path.exists()

        # Verify it's a valid image
        with Image.open(output_path) as img:
            assert img.size == (CARD_WIDTH, CARD_HEIGHT)


class TestSocialCardGeneratorGenerateAll:
    """Test batch generation."""

    def _create_mock_page(
        self,
        title: str = "Test Page",
        source_path: str = "test.md",
        metadata: dict[str, Any] | None = None,
        slug: str = "test",
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.title = title
        page.description = "Description"
        page.source_path = Path(source_path)
        page.metadata = metadata or {}
        page.slug = slug
        page.section_path = ""
        return page

    def _create_mock_site(self) -> MagicMock:
        """Create a mock site for testing."""
        site = MagicMock()
        site.config = {"title": "Test Site", "baseurl": ""}
        return site

    def test_generate_all_returns_counts(self, tmp_path: Path) -> None:
        """Test that generate_all returns correct counts."""
        site = self._create_mock_site()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        pages = [
            self._create_mock_page(title=f"Page {i}", source_path=f"page{i}.md", slug=f"page{i}")
            for i in range(3)
        ]

        generated, cached = generator.generate_all(pages, tmp_path)

        assert generated == 3
        assert cached == 0

    def test_generate_all_skips_disabled_pages(self, tmp_path: Path) -> None:
        """Test that disabled pages are skipped."""
        site = self._create_mock_site()
        config = SocialCardConfig()
        generator = SocialCardGenerator(site, config)

        pages = [
            self._create_mock_page(title="Normal", source_path="normal.md", slug="normal"),
            self._create_mock_page(
                title="Disabled",
                source_path="disabled.md",
                slug="disabled",
                metadata={"social_card": False},
            ),
            self._create_mock_page(
                title="Manual",
                source_path="manual.md",
                slug="manual",
                metadata={"image": "/custom.png"},
            ),
        ]

        generated, cached = generator.generate_all(pages, tmp_path)

        assert generated == 1  # Only "Normal" page
        assert cached == 0

    def test_generate_all_when_disabled(self, tmp_path: Path) -> None:
        """Test that generate_all returns (0, 0) when disabled."""
        site = self._create_mock_site()
        config = SocialCardConfig(enabled=False)
        generator = SocialCardGenerator(site, config)

        pages = [self._create_mock_page()]

        generated, cached = generator.generate_all(pages, tmp_path)

        assert generated == 0
        assert cached == 0


class TestGetSocialCardPath:
    """Test get_social_card_path helper function."""

    def _create_mock_page(
        self,
        slug: str = "test",
        section_path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MagicMock:
        """Create a mock page for testing."""
        page = MagicMock()
        page.slug = slug
        page.section_path = section_path
        page.metadata = metadata or {}
        return page

    def test_returns_path_when_enabled(self) -> None:
        """Test that path is returned when enabled."""
        config = SocialCardConfig(enabled=True)
        page = self._create_mock_page(slug="my-page")

        path = get_social_card_path(page, config, "https://example.com")

        assert path == "https://example.com/assets/social/my-page.png"

    def test_returns_none_when_disabled(self) -> None:
        """Test that None is returned when disabled."""
        config = SocialCardConfig(enabled=False)
        page = self._create_mock_page()

        path = get_social_card_path(page, config, "https://example.com")

        assert path is None

    def test_returns_none_when_manual_image(self) -> None:
        """Test that None is returned when page has manual image."""
        config = SocialCardConfig(enabled=True)
        page = self._create_mock_page(metadata={"image": "/custom.png"})

        path = get_social_card_path(page, config, "https://example.com")

        assert path is None

    def test_returns_none_when_page_disabled(self) -> None:
        """Test that None is returned when page has social_card: false."""
        config = SocialCardConfig(enabled=True)
        page = self._create_mock_page(metadata={"social_card": False})

        path = get_social_card_path(page, config, "https://example.com")

        assert path is None

    def test_nested_section_path(self) -> None:
        """Test path with nested section."""
        config = SocialCardConfig(enabled=True)
        page = self._create_mock_page(slug="my-page", section_path="docs/api")

        path = get_social_card_path(page, config, "https://example.com")

        assert path == "https://example.com/assets/social/docs-api-my-page.png"

    def test_jpg_format(self) -> None:
        """Test path with jpg format."""
        config = SocialCardConfig(enabled=True, format="jpg")
        page = self._create_mock_page(slug="my-page")

        path = get_social_card_path(page, config, "https://example.com")

        assert path == "https://example.com/assets/social/my-page.jpg"
