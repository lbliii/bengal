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
    params_config = _create_params_config(template)
    build_config = _create_build_config()
    features_config = _create_features_config()
    menu_config = _create_menu_config(template)
    search_config = _create_search_config(template)
    fonts_config = _create_fonts_config()

    # Write default configs
    _write_yaml(defaults / "site.yaml", site_config)
    _write_yaml(defaults / "theme.yaml", theme_config)
    _write_yaml(defaults / "content.yaml", content_config)
    _write_yaml(defaults / "params.yaml", params_config)
    _write_yaml(defaults / "build.yaml", build_config)
    _write_yaml(defaults / "features.yaml", features_config)
    _write_yaml(defaults / "menu.yaml", menu_config)
    _write_yaml(defaults / "search.yaml", search_config)
    _write_yaml(defaults / "fonts.yaml", fonts_config)

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
    cli.info("   │  ├─ _default/menu.yaml")
    cli.info("   │  ├─ _default/search.yaml")
    cli.info("   │  ├─ _default/fonts.yaml")
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
                # "content.math",  # LaTeX math via KaTeX (opt-in, ~200KB)
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


def _create_params_config(template: str) -> dict[str, Any]:
    """Create params configuration. Blog template gets contact placeholders."""
    params: dict[str, Any] = {}
    if template == "blog":
        params = {
            "email": "hello@example.com",
            "social": [
                {"name": "GitHub", "url": "https://github.com/yourusername"},
                {"name": "Twitter", "url": "https://twitter.com/yourusername"},
                {"name": "LinkedIn", "url": "https://linkedin.com/in/yourprofile"},
            ],
        }
    return {"params": params}


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
            "toc_depth": 3,
            "toc_min_headings": 2,
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
    """Create build configuration.

    Note: We don't set `incremental` here - it auto-detects based on cache presence.
    First build will be full (no cache), subsequent builds will be incremental (cache exists).

    """
    return {
        "build": {
            "output_dir": "public",
            # parallel: auto-detected via should_parallelize() based on page count
            # incremental: auto-detected based on cache presence
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
        },
        "social_cards": {
            "enabled": False,
            "template": "default",
            "background_color": "#0f172a",
            "text_color": "#f8fafc",
            "accent_color": "#06b6d4",
        },
    }


def _create_menu_config(template: str) -> dict[str, Any]:
    """Create menu configuration. Extra items appended to auto-generated nav."""
    return {
        "menu": {
            "extra": [],
        },
    }


def _create_search_config(template: str) -> dict[str, Any]:
    """Create search configuration."""
    placeholder = "Search documentation..." if template in ["docs", "documentation"] else "Search..."
    return {
        "search": {
            "enabled": True,
            "lunr": {
                "prebuilt": True,
                "min_query_length": 2,
                "max_results": 50,
                "preload": "smart",
            },
            "ui": {
                "modal": True,
                "recent_searches": 5,
                "placeholder": placeholder,
            },
        },
    }


def _create_fonts_config() -> dict[str, Any]:
    """Create font configuration."""
    return {
        "fonts": {
            "display": "Outfit:400,600,700",
        },
    }


def _create_local_env_config() -> dict[str, Any]:
    """Create local development environment config.

    Empty baseurl keeps links relative (/posts/foo/) so they work on any port
    (dev server default 5173, or user-configured). Avoids broken links when
    baseurl pointed at wrong port.
    """
    return {
        "site": {
            "baseurl": "",
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
