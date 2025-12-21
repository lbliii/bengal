"""
Factory methods for Site creation.

Provides classmethod factories for creating Site instances from configuration
files or for testing purposes.

Related Modules:
    - bengal.core.site.core: Main Site dataclass
    - bengal.config.loader: Configuration loading
    - bengal.config.directory_loader: Directory-based config loading
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    pass


class SiteFactoriesMixin:
    """
    Mixin providing factory methods for Site creation.

    This is a classmethod mixin - methods here are called on the class, not instances.
    """

    @classmethod
    def from_config(
        cls,
        root_path: Path,
        config_path: Path | None = None,
        environment: str | None = None,
        profile: str | None = None,
    ) -> Self:
        """
        Create a Site instance from configuration.

        This is the PREFERRED way to create a Site - it loads configuration
        from config/ directory or single config file and applies all settings.

        Config Loading (Priority):
            1. config/ directory (if exists) - Environment-aware, profile-native
            2. bengal.yaml / bengal.toml (single file) - Traditional
            3. Auto-detect environment from platform (Netlify, Vercel, GitHub Actions)

        Directory Structure (Recommended):
            config/
            ├── _default/          # Base config
            │   ├── site.yaml
            │   ├── build.yaml
            │   └── features.yaml
            ├── environments/      # Environment overrides
            │   ├── local.yaml
            │   ├── preview.yaml
            │   └── production.yaml
            └── profiles/          # Build profiles
                ├── writer.yaml
                ├── theme-dev.yaml
                └── dev.yaml

        Important Config Sections:
            - [site]: title, baseurl, author, etc.
            - [build]: parallel, max_workers, incremental, etc.
            - [markdown]: parser selection ('mistune' recommended)
            - [features]: rss, sitemap, search, json, etc.
            - [taxonomies]: tags, categories, series

        Args:
            root_path: Root directory of the site (Path object)
            config_path: Optional explicit path to config file (Path object)
                        Only used for single-file configs, ignored if config/ exists
            environment: Environment name (e.g., 'production', 'local')
                        Auto-detected if not specified (Netlify, Vercel, GitHub)
            profile: Profile name (e.g., 'writer', 'dev')
                        Optional, only applies if config/ directory exists

        Returns:
            Configured Site instance with all settings loaded

        Examples:
            # Auto-detect config (prefers config/ directory)
            site = Site.from_config(Path('/path/to/site'))

            # Explicit environment
            site = Site.from_config(
                Path('/path/to/site'),
                environment='production'
            )

            # With profile
            site = Site.from_config(
                Path('/path/to/site'),
                environment='local',
                profile='dev'
            )

        For Testing:
            If you need a Site for testing, use Site.for_testing() instead.
            It creates a minimal Site without requiring a config file.

        See Also:
            - Site() - Direct constructor for advanced use cases
            - Site.for_testing() - Factory for test sites
        """
        config_dir = root_path / "config"

        if config_dir.exists() and config_dir.is_dir():
            from bengal.config.directory_loader import ConfigDirectoryLoader

            loader = ConfigDirectoryLoader()
            config = loader.load(config_dir, environment=environment, profile=profile)
        else:
            # Fall back to single-file config
            # ConfigLoader.load() handles None config_path by searching for
            # bengal.toml/yaml and returning defaults if not found
            from bengal.config.loader import ConfigLoader

            loader = ConfigLoader(root_path)
            config = loader.load(config_path)

        return cls(root_path=root_path, config=config)

    @classmethod
    def for_testing(
        cls, root_path: Path | None = None, config: dict[str, Any] | None = None
    ) -> Self:
        """
        Create a Site instance for testing without requiring a config file.

        This is a convenience factory for unit tests and integration tests
        that need a Site object with custom configuration.

        Args:
            root_path: Root directory of the test site (defaults to current dir)
            config: Configuration dictionary (defaults to minimal config)

        Returns:
            Configured Site instance ready for testing

        Example:
            # Minimal test site
            site = Site.for_testing()

            # Test site with custom root path
            site = Site.for_testing(Path('/tmp/test_site'))

            # Test site with custom config
            config = {'site': {'title': 'My Test Site'}}
            site = Site.for_testing(config=config)

        Note:
            This bypasses config file loading, so you control all settings.
            Perfect for unit tests that need predictable behavior.
        """
        if root_path is None:
            root_path = Path(".")

        if config is None:
            config = {
                "site": {"title": "Test Site"},
                "build": {"output_dir": "public"},
            }

        return cls(root_path=root_path, config=config)
