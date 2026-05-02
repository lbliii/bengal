"""CI cache input discovery helpers.

This module backs ``bengal cache inputs`` and ``bengal cache hash``. It keeps
cache-key input discovery outside the CLI layer so command-framework migrations
do not change the cache contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Protocol

    class CacheInputSite(Protocol):
        root_path: Path
        config: Any


def get_input_globs(site: CacheInputSite) -> list[tuple[str, str]]:
    """Return ``(glob_pattern, source_description)`` tuples for build inputs.

    Patterns are relative to ``site.root_path`` unless they start with ``../``.
    They represent inputs that can affect rendered output and therefore should
    participate in CI cache-key generation.
    """
    inputs: list[tuple[str, str]] = []
    site_root = site.root_path

    inputs.append(("content/**", "built-in"))
    inputs.append(("config/**", "built-in"))

    templates_dir = site_root / "templates"
    if templates_dir.exists():
        inputs.append(("templates/**", "custom templates"))

    static_dir = site_root / "static"
    if static_dir.exists():
        inputs.append(("static/**", "static assets"))

    assets_dir = site_root / "assets"
    if assets_dir.exists():
        inputs.append(("assets/**", "assets"))

    config = site.config

    autodoc_config = config.get("autodoc", {})
    python_config = autodoc_config.get("python", {})
    if python_config.get("enabled", False):
        source_dirs = python_config.get("source_dirs", [])
        inputs.extend(
            (f"{source_dir}/**/*.py", "autodoc.python.source_dirs") for source_dir in source_dirs
        )

    cli_config = autodoc_config.get("cli", {})
    if cli_config.get("enabled", False):
        app_module = cli_config.get("app_module")
        if app_module:
            package = app_module.split(":")[0].split(".")[0]
            inputs.append((f"../{package}/**/*.py", "autodoc.cli.app_module"))

    openapi_config = autodoc_config.get("openapi", {})
    if openapi_config.get("enabled", False):
        spec_file = openapi_config.get("spec_file")
        if spec_file:
            inputs.append((spec_file, "autodoc.openapi.spec_file"))

    external_refs = config.get("external_refs", {})
    if isinstance(external_refs, dict) and external_refs.get("enabled", True):
        indexes = external_refs.get("indexes", [])
        for index in indexes:
            url = index.get("url", "") if isinstance(index, dict) else ""
            if url and not url.startswith(("http://", "https://")):
                inputs.append((url, "external_refs.indexes"))

    theme_config = config.get("theme", {})
    theme_path = theme_config.get("path") if isinstance(theme_config, dict) else None
    if theme_path:
        inputs.append((f"{theme_path}/**", "theme.path"))

    themes_dir = site_root / "themes"
    if themes_dir.exists():
        inputs.append(("themes/**", "local themes"))

    return inputs
