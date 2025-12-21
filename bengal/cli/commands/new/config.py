"""
Configuration directory generation for new Bengal sites.

Creates the config/ directory structure with environment-aware configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bengal.output import CLIOutput


def create_config_directory(
    site_path: Path,
    site_title: str,
    theme: str,
    cli: CLIOutput,
    template: str = "default",
    baseurl: str = "https://example.com",
) -> None:
    """
    Create config directory structure with sensible defaults.

    Args:
        site_path: Root path for the new site
        site_title: Title for the site
        theme: Theme name to use
        cli: CLI output helper for logging
        template: Site template type (blog, docs, portfolio, resume, default)
        baseurl: Base URL for the site
    """
    config_dir = site_path / "config"

    # Create directories
    defaults = config_dir / "_default"
    defaults.mkdir(parents=True, exist_ok=True)

    envs = config_dir / "environments"
    envs.mkdir(exist_ok=True)

    # Create default configs
    site_config = _create_site_config(site_title, baseurl)
    theme_config = _create_theme_config(theme)
    content_config = _create_content_config(template)
    params_config: dict[str, Any] = {"params": {}}
    build_config = _create_build_config()
    features_config = _create_features_config()

    # Write default configs
    _write_yaml(defaults / "site.yaml", site_config)
    _write_yaml(defaults / "theme.yaml", theme_config)
    _write_yaml(defaults / "content.yaml", content_config)
    _write_yaml(defaults / "params.yaml", params_config)
    _write_yaml(defaults / "build.yaml", build_config)
    _write_yaml(defaults / "features.yaml", features_config)

    # Create environment configs
    local_config = _create_local_env_config()
    production_config = _create_production_env_config()

    _write_yaml(envs / "local.yaml", local_config)
    _write_yaml(envs / "production.yaml", production_config)

    cli.info("   ├─ Created config/ directory:")
    cli.info("   │  ├─ _default/site.yaml")
    cli.info("   │  ├─ _default/theme.yaml")
    cli.info("   │  ├─ _default/content.yaml")
    cli.info("   │  ├─ _default/params.yaml")
    cli.info("   │  ├─ _default/build.yaml")
    cli.info("   │  ├─ _default/features.yaml")
    cli.info("   │  ├─ environments/local.yaml")
    cli.info("   │  └─ environments/production.yaml")


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write data as YAML to file."""
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def _create_site_config(site_title: str, baseurl: str) -> dict[str, Any]:
    """Create site configuration."""
    return {
        "site": {
            "title": site_title,
            "baseurl": baseurl,
            "description": f"{site_title} - Built with Bengal",
            "language": "en",
        }
    }


def _create_theme_config(theme: str) -> dict[str, Any]:
    """Create theme configuration."""
    return {
        "theme": {
            "name": theme,
            "default_appearance": "dark",
            "default_palette": "snow-lynx",
            "features": [
                # Navigation
                "navigation.breadcrumbs",
                "navigation.toc",
                "navigation.toc.sticky",
                "navigation.prev_next",
                "navigation.back_to_top",
                # Content
                "content.code.copy",
                "content.lightbox",
                "content.reading_time",
                "content.author",
                "content.excerpts",
                "content.children",
                # Search
                "search.suggest",
                "search.highlight",
                # Footer
                "footer.social",
                # Accessibility
                "accessibility.skip_link",
            ],
            "max_tags_display": 10,
            "popular_tags_count": 20,
        }
    }


def _create_content_config(template: str) -> dict[str, Any]:
    """Create content configuration based on template type."""
    content_config: dict[str, Any] = {"content": {}}

    if template == "blog":
        content_config["content"] = {
            "default_type": "blog",
            "excerpt_length": 200,
            "reading_speed": 200,
            "related_count": 5,
            "sort_pages_by": "date",
            "sort_order": "desc",  # Newest first for blogs
        }
    elif template in ["docs", "documentation"]:
        content_config["content"] = {
            "default_type": "doc",
            "excerpt_length": 200,
            "reading_speed": 200,
            "toc_depth": 4,
            "toc_min_headings": 2,
            "sort_pages_by": "weight",
            "sort_order": "asc",
        }
    elif template == "resume":
        content_config["content"] = {
            "default_type": "resume",
            "excerpt_length": 150,
            "sort_pages_by": "weight",
            "sort_order": "asc",
        }
    elif template == "portfolio":
        content_config["content"] = {
            "default_type": "page",
            "excerpt_length": 200,
            "sort_pages_by": "date",
            "sort_order": "desc",
        }
    else:  # default
        content_config["content"] = {
            "default_type": "page",
            "excerpt_length": 200,
            "reading_speed": 200,
            "sort_pages_by": "weight",
            "sort_order": "asc",
        }

    return content_config


def _create_build_config() -> dict[str, Any]:
    """Create build configuration."""
    return {
        "build": {
            "output_dir": "public",
            "parallel": True,
            "incremental": True,
        },
        "assets": {
            "minify": True,
            "fingerprint": True,
        },
    }


def _create_features_config() -> dict[str, Any]:
    """Create features configuration."""
    return {
        "features": {
            "rss": True,
            "sitemap": True,
            "search": True,
            "json": True,
            "llm_txt": True,
            "syntax_highlighting": True,
        }
    }


def _create_local_env_config() -> dict[str, Any]:
    """Create local development environment config."""
    return {
        "site": {
            "baseurl": "http://localhost:8000",
        },
        "build": {
            "parallel": False,  # Easier debugging
        },
        "assets": {
            "minify": False,  # Faster builds
            "fingerprint": False,
        },
    }


def _create_production_env_config() -> dict[str, Any]:
    """Create production environment config."""
    return {
        "site": {
            "baseurl": "https://example.com",  # User will update this
        },
        "build": {
            "parallel": True,
            "strict_mode": True,
        },
    }
