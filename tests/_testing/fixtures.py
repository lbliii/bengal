"""
Shared pytest fixtures for Bengal test suite.

Provides:
- rootdir: Path to tests/roots/ directory
- site_factory: Factory to create Site from test roots
- site_builder: Factory to create ephemeral sites from config/content dicts
- build_site: Helper to build a site
"""

import shutil
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import tomli_w

from bengal.core.site import Site


@pytest.fixture(scope="session")
def rootdir() -> Path:
    """
    Path to tests/roots/ directory containing test site templates.

    Session-scoped since the directory doesn't change during test run.
    """
    return Path(__file__).parent.parent / "roots"


@pytest.fixture
def site_factory(tmp_path: Path, rootdir: Path) -> Callable:
    """
    Factory to create Site instances from test roots.

    Usage:
        def test_something(site_factory):
            site = site_factory("test-basic")
            # or with overrides:
            site = site_factory("test-basic", confoverrides={"site.title": "Custom"})

    Args:
        testroot: Name of the root under tests/roots/
        confoverrides: Dict of config overrides to apply

    Returns:
        Configured Site instance (content/assets already discovered)
    """

    def _factory(testroot: str, confoverrides: dict[str, Any] | None = None) -> Site:
        # Validate testroot exists
        root_path = rootdir / testroot
        if not root_path.exists():
            available = [p.name for p in rootdir.iterdir() if p.is_dir()]
            raise ValueError(
                f"Test root '{testroot}' not found. Available roots: {', '.join(available)}"
            )

        # Create site directory
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Check if skeleton manifest exists - use it if available
        skeleton_manifest = root_path / "skeleton.yaml"
        if skeleton_manifest.exists():
            # Use skeleton manifest to create structure
            from bengal.cli.skeleton.hydrator import Hydrator
            from bengal.cli.skeleton.schema import Skeleton

            skeleton = Skeleton.from_yaml(skeleton_manifest.read_text())
            content_dir = site_dir / "content"
            content_dir.mkdir()

            hydrator = Hydrator(content_dir, dry_run=False, force=True)
            hydrator.apply(skeleton)

            # Copy config and other files from root
            for item in root_path.iterdir():
                if item.name not in ("skeleton.yaml", "content"):
                    if item.is_file():
                        shutil.copy2(item, site_dir / item.name)
                    elif item.is_dir() and item.name != "public":  # Skip public/build artifacts
                        shutil.copytree(item, site_dir / item.name, dirs_exist_ok=True)
        else:
            # Fallback: Copy entire root (backward compatibility)
            shutil.copytree(root_path, site_dir, dirs_exist_ok=True)

        # Apply config overrides if provided
        if confoverrides:
            config_path = site_dir / "bengal.toml"
            if config_path.exists():
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

                # Apply nested overrides (e.g., "site.title" -> config["site"]["title"])
                for key, value in confoverrides.items():
                    if "." in key:
                        section, subkey = key.split(".", 1)
                        if section not in config:
                            config[section] = {}
                        config[section][subkey] = value
                    else:
                        config[key] = value

                # Write back
                with open(config_path, "wb") as f:
                    tomli_w.dump(config, f)

        # Create and initialize Site
        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()

        return site

    return _factory


@pytest.fixture
def build_site(request) -> Callable:
    """
    Helper to build a site instance.

    Usage:
        def test_something(site, build_site):
            build_site()  # Builds site with default options
            # or:
            build_site(parallel=False, incremental=True)

    Automatically injects 'site' from test parameters if present.
    """

    def _build(parallel: bool = False, incremental: bool = False) -> None:
        # Try to get site from test parameters
        if hasattr(request, "getfixturevalue"):
            try:
                site = request.getfixturevalue("site")
            except Exception as e:
                raise RuntimeError(
                    "build_site requires 'site' fixture. "
                    "Add 'site' parameter to your test function."
                ) from e
        else:
            raise RuntimeError("build_site requires pytest request fixture")

        site.build(parallel=parallel, incremental=incremental)

    return _build


@dataclass
class EphemeralSite:
    """
    Wrapper for ephemeral test sites created by site_builder.

    Provides convenient methods for building and inspecting output.
    """

    site: Site
    site_dir: Path
    output_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.output_dir = self.site_dir / "public"

    def build(self, parallel: bool = False, incremental: bool = False) -> None:
        """Build the site."""
        self.site.build(parallel=parallel, incremental=incremental)

    def read_output(self, path: str) -> str:
        """Read a file from the output directory."""
        output_path = self.output_dir / path
        if not output_path.exists():
            raise FileNotFoundError(f"Output file not found: {output_path}")
        return output_path.read_text()

    def output_exists(self, path: str) -> bool:
        """Check if an output file exists."""
        return (self.output_dir / path).exists()


@pytest.fixture
def site_builder(tmp_path: Path) -> Callable:
    """
    Factory to create ephemeral sites from config and content dicts.

    Usage:
        def test_something(site_builder):
            site = site_builder(
                config={"title": "Test Site", "document_application": {"enabled": True}},
                content={"_index.md": "---\\ntitle: Home\\n---\\nWelcome"}
            )
            site.build()
            html = site.read_output("index.html")
            assert "Welcome" in html

    Args:
        config: Dict of site configuration (nested structure)
        content: Dict mapping relative paths to content strings

    Returns:
        EphemeralSite instance with build() and read_output() methods
    """

    def _factory(
        config: dict[str, Any] | None = None,
        content: dict[str, str] | None = None,
    ) -> EphemeralSite:
        # Create site directory
        site_dir = tmp_path / "ephemeral_site"
        site_dir.mkdir(exist_ok=True)

        # Build config with sensible defaults
        full_config: dict[str, Any] = {
            "site": {
                "title": "Test Site",
                "baseurl": "/",
            },
            "build": {
                "output_dir": "public",
            },
        }

        # Merge provided config
        if config:
            for key, value in config.items():
                if (
                    key in full_config
                    and isinstance(full_config[key], dict)
                    and isinstance(value, dict)
                ):
                    full_config[key].update(value)
                else:
                    full_config[key] = value

        # Write config file
        config_path = site_dir / "bengal.toml"
        with open(config_path, "wb") as f:
            tomli_w.dump(full_config, f)

        # Create content directory and files
        content_dir = site_dir / "content"
        content_dir.mkdir(exist_ok=True)

        if content:
            for rel_path, file_content in content.items():
                file_path = content_dir / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_content)

        # Create and initialize Site
        site = Site.from_config(site_dir)
        site.discover_content()
        site.discover_assets()

        return EphemeralSite(site=site, site_dir=site_dir)

    return _factory
