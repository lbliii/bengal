"""
Shared pytest fixtures for Bengal test suite.

Provides:
- rootdir: Path to tests/roots/ directory
- site_factory: Factory to create Site from test roots
- build_site: Helper to build a site
"""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import toml

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
                config = toml.load(config_path)

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
                with open(config_path, "w") as f:
                    toml.dump(config, f)

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
