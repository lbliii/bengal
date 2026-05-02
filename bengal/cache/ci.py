"""CI cache input discovery helpers.

This module backs ``bengal cache inputs`` and ``bengal cache hash``. It keeps
cache-key input discovery outside the CLI layer so command-framework migrations
do not change the cache contract.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Protocol

    class CacheInputSite(Protocol):
        root_path: Path
        config: Any


def _config_section(config: Any, name: str) -> Any:
    if isinstance(config, dict):
        return config.get(name, {})
    get = getattr(config, "get", None)
    if callable(get):
        return get(name, {})
    return getattr(config, name, {})


def _config_value(config: Any, section: str, key: str, default: str) -> str:
    section_config = _config_section(config, section)
    if isinstance(section_config, dict):
        value = section_config.get(key)
    else:
        value = getattr(section_config, key, None)
    return str(value or default)


def _path_pattern(site_root: Path, raw_path: str, suffix: str = "") -> str:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        try:
            return f"{path.relative_to(site_root).as_posix()}{suffix}"
        except ValueError:
            pass
        return f"{path.as_posix()}{suffix}"

    if raw_path.startswith("../") and raw_path.count("../") > 1:
        return f"{(site_root / path).resolve().as_posix()}{suffix}"

    return f"{path.as_posix()}{suffix}"


def _add_input(inputs: list[tuple[str, str]], seen: set[str], pattern: str, source: str) -> None:
    if pattern in seen:
        return
    seen.add(pattern)
    inputs.append((pattern, source))


def _add_existing_dir(
    inputs: list[tuple[str, str]],
    seen: set[str],
    site_root: Path,
    dir_name: str,
    source: str,
) -> None:
    path = Path(dir_name)
    resolved = path if path.is_absolute() else site_root / path
    if resolved.exists():
        _add_input(inputs, seen, _path_pattern(site_root, dir_name, "/**"), source)


def _add_existing_file(
    inputs: list[tuple[str, str]],
    seen: set[str],
    site_root: Path,
    file_name: str,
    source: str,
) -> None:
    path = Path(file_name)
    resolved = path if path.is_absolute() else site_root / path
    if resolved.exists():
        _add_input(inputs, seen, _path_pattern(site_root, file_name), source)


def _cli_module_patterns(site_root: Path, app_module: str) -> list[str]:
    module_path = app_module.split(":", 1)[0]
    try:
        spec = importlib.util.find_spec(module_path)
    except ImportError, AttributeError, ValueError:
        spec = None

    patterns: list[str] = []
    if spec is not None and spec.submodule_search_locations:
        patterns.extend(
            f"{Path(location).as_posix()}/**/*.py" for location in spec.submodule_search_locations
        )
    elif spec is not None and spec.origin and spec.origin not in {"built-in", "frozen"}:
        patterns.append(Path(spec.origin).as_posix())

    if patterns:
        return patterns

    package = module_path.split(".")[0]
    return [_path_pattern(site_root, f"../{package}", "/**/*.py")]


def get_input_globs(
    site: CacheInputSite, config_path: str | Path | None = None
) -> list[tuple[str, str]]:
    """Return ``(glob_pattern, source_description)`` tuples for build inputs.

    Patterns are relative to ``site.root_path`` unless they start with ``../``.
    They represent inputs that can affect rendered output and therefore should
    participate in CI cache-key generation.
    """
    inputs: list[tuple[str, str]] = []
    seen: set[str] = set()
    site_root = site.root_path
    config = site.config

    build_content_dir = _config_value(config, "build", "content_dir", "content")
    content_dir = getattr(site, "content_dir", None)
    content_dir_pattern = (
        _path_pattern(site_root, str(content_dir), "/**")
        if content_dir is not None
        else _path_pattern(site_root, build_content_dir, "/**")
    )
    _add_input(inputs, seen, content_dir_pattern, "content")
    if content_dir is None or Path(build_content_dir) != Path(content_dir).name:
        _add_existing_dir(inputs, seen, site_root, build_content_dir, "build.content_dir")

    _add_input(inputs, seen, "config/**", "config directory")
    for config_file in ("bengal.toml", "bengal.yaml", "bengal.yml"):
        _add_existing_file(inputs, seen, site_root, config_file, "site config")
    if config_path:
        _add_existing_file(inputs, seen, site_root, str(config_path), "cli --config")

    templates_dir = _config_value(config, "build", "templates_dir", "templates")
    _add_existing_dir(inputs, seen, site_root, templates_dir, "custom templates")

    static_config = _config_section(config, "static")
    static_enabled = (
        static_config.get("enabled", True)
        if isinstance(static_config, dict)
        else getattr(static_config, "enabled", True)
    )
    if static_config is not False and static_enabled:
        static_dir = (
            static_config.get("dir", "static")
            if isinstance(static_config, dict)
            else getattr(static_config, "dir", "static")
        )
        _add_existing_dir(inputs, seen, site_root, str(static_dir), "static assets")

    assets_dir = _config_value(config, "build", "assets_dir", "assets")
    _add_existing_dir(inputs, seen, site_root, assets_dir, "assets")
    _add_existing_dir(inputs, seen, site_root, "data", "site data")
    _add_existing_dir(inputs, seen, site_root, "i18n", "translations")

    autodoc_config = _config_section(config, "autodoc")
    python_config = autodoc_config.get("python", {})
    if python_config.get("enabled", False):
        source_dirs = python_config.get("source_dirs", [])
        for source_dir in source_dirs:
            _add_input(
                inputs,
                seen,
                _path_pattern(site_root, str(source_dir), "/**/*.py"),
                "autodoc.python.source_dirs",
            )

    cli_config = autodoc_config.get("cli", {})
    if cli_config.get("enabled", False):
        app_module = cli_config.get("app_module")
        if app_module:
            for pattern in _cli_module_patterns(site_root, str(app_module)):
                _add_input(inputs, seen, pattern, "autodoc.cli.app_module")

    openapi_config = autodoc_config.get("openapi", {})
    if openapi_config.get("enabled", False):
        spec_file = openapi_config.get("spec_file")
        if spec_file:
            _add_input(
                inputs,
                seen,
                _path_pattern(site_root, str(spec_file)),
                "autodoc.openapi.spec_file",
            )

    external_refs = _config_section(config, "external_refs")
    if isinstance(external_refs, dict) and external_refs.get("enabled", True):
        indexes = external_refs.get("indexes", [])
        for index in indexes:
            url = index.get("url", "") if isinstance(index, dict) else ""
            if url and not url.startswith(("http://", "https://")):
                _add_input(
                    inputs,
                    seen,
                    _path_pattern(site_root, url),
                    "external_refs.indexes",
                )

    theme_config = _config_section(config, "theme")
    theme_path = theme_config.get("path") if isinstance(theme_config, dict) else None
    if theme_path:
        _add_input(inputs, seen, _path_pattern(site_root, str(theme_path), "/**"), "theme.path")

    _add_existing_dir(inputs, seen, site_root, "themes", "local themes")

    return inputs
