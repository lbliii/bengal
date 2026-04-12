"""
Theme library provider resolution.

Resolves external Kida UI library packages declared in theme.toml into
normalized provider records. Providers expose template loaders, static
asset roots, and environment registration hooks via a convention-based
contract on the imported package module.

Convention hooks (all optional on the package):
    get_loader() -> Any         # returns a Kida/Jinja PackageLoader
    static_path() -> Path       # returns the package's static asset root
    register_filters(app) -> None  # registers filters/globals via an adapter

Key Concepts:
- Themes declare libraries in theme.toml: libraries = ["chirp_ui"]
- Bengal imports each package and probes for convention hooks
- Missing hooks are treated as absent capabilities, not errors
- Import failure or invalid hooks produce a BengalConfigError

Related Modules:
- bengal.core.theme.resolution: Theme manifest parsing and chain building
- bengal.rendering.engines.kida: Kida engine that mounts provider loaders

"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ThemeLibraryProvider:
    """Normalized provider record for an external Kida UI library.

    Created by resolve_provider() from a convention-based package.
    Immutable and safe for concurrent access during parallel rendering.

    """

    package: str
    loader: Any | None
    asset_root: Path | None
    asset_prefix: str
    register_env: Callable[[Any], None] | None


def resolve_provider(package_name: str) -> ThemeLibraryProvider:
    """Import a library package and normalize its convention hooks.

    Probes the package module for get_loader(), static_path(), and
    register_filters(). Missing hooks produce None fields, not errors.
    Import failure or hook invocation errors raise BengalConfigError.

    Args:
        package_name: Python package name (e.g., "chirp_ui").

    Returns:
        ThemeLibraryProvider with resolved hooks.

    Raises:
        BengalConfigError: If the package cannot be imported or a hook fails.

    """
    from bengal.errors.exceptions import BengalConfigError

    try:
        module = importlib.import_module(package_name)
    except ImportError as e:
        msg = (
            f"Theme library '{package_name}' is not installed. "
            f"Install it or remove it from the theme's libraries list."
        )
        raise BengalConfigError(msg) from e
    except Exception as e:
        msg = f"Theme library '{package_name}' failed to import: {e}"
        raise BengalConfigError(msg) from e

    loader = _probe_hook(package_name, module, "get_loader")
    asset_root_raw = _probe_hook(package_name, module, "static_path")
    asset_root: Path | None = None
    if asset_root_raw is not None:
        from pathlib import Path as _Path

        try:
            asset_root = _Path(asset_root_raw)
        except TypeError as e:
            msg = (
                f"Theme library '{package_name}': static_path() returned "
                f"{type(asset_root_raw).__name__}, expected a path-like object"
            )
            raise BengalConfigError(msg) from e
    register_filters_fn = getattr(module, "register_filters", None)

    register_env: Callable[[Any], None] | None = None
    if callable(register_filters_fn):
        register_env = register_filters_fn

    asset_prefix = package_name.replace("-", "_").replace(".", "_")

    logger.debug(
        "theme_library_provider_resolved",
        package=package_name,
        has_loader=loader is not None,
        has_asset_root=asset_root is not None,
        has_register_env=register_env is not None,
    )

    return ThemeLibraryProvider(
        package=package_name,
        loader=loader,
        asset_root=asset_root,
        asset_prefix=asset_prefix,
        register_env=register_env,
    )


def resolve_theme_providers(
    site_root: Path,
    theme_chain: list[str],
) -> tuple[ThemeLibraryProvider, ...]:
    """Accumulate library providers from the theme inheritance chain.

    For each theme in the chain, reads its theme.toml for libraries,
    resolves each to a ThemeLibraryProvider, and deduplicates by package
    name (earlier theme in chain — i.e. child — wins).

    Args:
        site_root: Site root directory.
        theme_chain: Theme names from child to parent.

    Returns:
        Tuple of deduplicated ThemeLibraryProvider records.

    """
    from bengal.core.theme.resolution import _read_theme_manifest

    seen: set[str] = set()
    providers: list[ThemeLibraryProvider] = []

    for theme_name in theme_chain:
        manifest = _read_theme_manifest(site_root, theme_name)
        for lib_name in manifest.libraries:
            if lib_name not in seen:
                seen.add(lib_name)
                provider = resolve_provider(lib_name)
                providers.append(provider)

    return tuple(providers)


def get_provider_asset_dirs(
    providers: tuple[ThemeLibraryProvider, ...],
) -> list[tuple[str, Path]]:
    """Return (prefix, asset_root) pairs for providers that have asset roots.

    Each tuple maps a namespace prefix (the provider's asset_prefix) to
    the directory containing library static assets. The caller should emit
    assets under ``{prefix}/{relative_path}`` so they are namespaced.

    Args:
        providers: Resolved theme library providers.

    Returns:
        List of (prefix, path) tuples for providers with asset roots.

    """
    return [
        (p.asset_prefix, p.asset_root)
        for p in providers
        if p.asset_root is not None and p.asset_root.exists()
    ]


def _probe_hook(package_name: str, module: Any, hook_name: str) -> Any | None:
    """Call a convention hook on a library module, returning None if absent."""
    from bengal.errors.exceptions import BengalConfigError

    fn = getattr(module, hook_name, None)
    if fn is None or not callable(fn):
        return None
    try:
        return fn()
    except Exception as e:
        msg = f"Theme library '{package_name}': {hook_name}() failed: {e}"
        raise BengalConfigError(msg) from e
