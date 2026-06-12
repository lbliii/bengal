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
    get_library_contract() -> Mapping  # assets/runtime + version governance

The contract may also declare version governance fields that Bengal enforces at
provider-resolution time (build start), not mid-render:
    contract_version: int       # contract schema revision the library targets
    requires: Mapping[str, str] # distribution -> PEP 440 specifier, e.g.
                                # {"kida": ">=0.9.0"}

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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.lru_cache import LRUCache

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

_ASSET_MODES = frozenset({"bundle", "link", "none"})

# Theme-library contract version supported by this Bengal build.
#
# A theme library declares the contract revision it was built against via
# ``contract_version`` in get_library_contract(). Bengal accepts any library
# whose declared version is <= this value (older contracts are forward-readable;
# a NEWER contract than Bengal understands is rejected at resolution time so the
# failure surfaces at build start, not mid-render). Bump this when the contract
# schema gains a backwards-incompatible field.
SUPPORTED_CONTRACT_VERSION = 1

# Maps the short requirement keys a library may use in its contract ``requires``
# block to the actual installed distribution name queried via
# importlib.metadata. This lets a contract write the ergonomic
# ``requires = {"kida": ">=0.9.0"}`` while Bengal resolves the version of the
# real ``kida-templates`` wheel. Unknown keys are treated as literal
# distribution names.
_REQUIREMENT_DISTRIBUTIONS = {
    "kida": "kida-templates",
    "kida-templates": "kida-templates",
    "bengal": "bengal",
}

# Thread-safe cache for resolved theme-library providers.
#
# resolve_theme_providers() is invoked on two independent build paths with no
# shared state: asset discovery (orchestration/content.py) and Kida engine
# loader/filter setup (rendering/engines/kida.py). Under the #350 shard-parallel
# render path the Kida engine is constructed per-thread-local pipeline, so the
# providers would otherwise be re-imported (importlib.import_module + hook
# probing) once per worker thread on top of the asset-discovery pass -- i.e.
# strictly more than twice per build. Caching by (site_root, theme_chain)
# collapses all of that into a single resolution that every caller and shard
# thread shares.
#
# RLock-backed and free-threading-safe (CPython 3.14t): LRUCache.get_or_set
# computes the factory OUTSIDE the lock and resolves the simultaneous-miss race
# by re-checking under the lock before storing. maxsize=32 is generous; the key
# space is (site_root, chain), of which a single process sees very few distinct
# values (one per site in a multi-site build).
#
# Cache-key parity assumption: the two callers reach resolve_theme_providers()
# via two different resolve_theme_chain implementations
# (bengal.core.theme.resolution vs bengal.rendering.template_engine.environment).
# They produce the same chain for a given site today, so a single
# (site_root, theme_chain) key hits across both. If one diverges later the cache
# would simply miss and recompute -- a perf regression, never a correctness bug.
_provider_cache: LRUCache[tuple[str, tuple[str, ...]], tuple[ThemeLibraryProvider, ...]] = LRUCache(
    maxsize=32, name="theme_providers"
)


def _theme_library_debug_payload(
    package_name: str,
    *,
    hook_name: str | None = None,
    returned_type: str | None = None,
) -> Any:
    """Build structured debug context for theme library provider errors."""
    from bengal.errors.context import ErrorDebugPayload

    relevant_config: dict[str, Any] = {"library": package_name}
    grep_patterns = [f"libraries = .*{package_name}"]
    if hook_name is not None:
        relevant_config["hook"] = hook_name
        grep_patterns.append(f"def {hook_name}")
    if returned_type is not None:
        relevant_config["returned_type"] = returned_type

    return ErrorDebugPayload(
        processing_item=f"theme-library:{package_name}",
        processing_type="theme_library",
        config_keys_accessed=["theme.libraries"],
        relevant_config=relevant_config,
        files_to_check=["themes/*/theme.toml", package_name],
        grep_patterns=grep_patterns,
    )


@dataclass(frozen=True, slots=True)
class LibraryAsset:
    """A browser-downloadable asset declared by a theme library contract."""

    source_path: Path
    logical_path: Path
    asset_type: str
    mode: str
    package: str = ""
    contract_path: Path | None = None
    tag_attrs: tuple[tuple[str, str | bool], ...] = field(default_factory=tuple)


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
    assets: tuple[LibraryAsset, ...] = field(default_factory=tuple)
    runtime: tuple[str, ...] = field(default_factory=tuple)


def resolve_provider(package_name: str) -> ThemeLibraryProvider:
    """Import a library package and normalize its convention hooks.

    Probes the package module for get_library_contract(), get_loader(),
    static_path(), and register_filters(). Missing hooks produce None fields,
    not errors.

    Before consuming the contract, applies the capability guard: a contract that
    declares ``contract_version`` newer than this Bengal build, or whose
    ``requires`` version specifiers are unsatisfied by the installed
    distributions (e.g. a skewed ``kida-templates``), raises BengalConfigError
    here -- at config/provider-resolution time -- rather than mid-render.

    Import failure or hook invocation errors raise BengalConfigError.

    Args:
        package_name: Python package name (e.g., "chirp_ui").

    Returns:
        ThemeLibraryProvider with resolved hooks.

    Raises:
        BengalConfigError: If the package cannot be imported or a hook fails.

    """
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    try:
        module = importlib.import_module(package_name)
    except ImportError as e:
        msg = (
            f"Theme library '{package_name}' is not installed. "
            f"Install it or remove it from the theme's libraries list."
        )
        raise BengalConfigError(
            msg,
            code=ErrorCode.C003,
            suggestion=(
                f"Install the '{package_name}' package in the build environment "
                "or remove it from the theme's libraries list."
            ),
            debug_payload=_theme_library_debug_payload(package_name),
        ) from e
    except Exception as e:
        msg = f"Theme library '{package_name}' failed to import: {e}"
        raise BengalConfigError(
            msg,
            code=ErrorCode.C003,
            suggestion=(
                f"Fix the import-time error in '{package_name}' or remove it "
                "from the theme's libraries list."
            ),
            debug_payload=_theme_library_debug_payload(package_name),
        ) from e

    contract_raw = _probe_hook(package_name, module, "get_library_contract")
    contract = _normalize_contract(package_name, contract_raw)

    # Capability guard: validate the library's declared contract version and
    # version requirements at resolution time (build start), so an incompatible
    # wheel fails loudly here instead of producing a BengalRenderingError on the
    # first page that touches a missing symbol.
    _check_contract_version(package_name, contract.get("contract_version"))
    _check_requirements(package_name, contract.get("requires"))

    loader = contract.get("loader") or contract.get("template_loader")
    if loader is None:
        loader = _probe_hook(package_name, module, "get_loader")

    asset_root = _normalize_asset_root(
        package_name,
        contract.get("asset_root") or contract.get("static_path"),
    )
    if asset_root is None:
        asset_root_raw = _probe_hook(package_name, module, "static_path")
        asset_root = _normalize_asset_root(package_name, asset_root_raw, hook_name="static_path")

    register_filters_fn = getattr(module, "register_filters", None)

    register_env: Callable[[Any], None] | None = None
    if callable(register_filters_fn):
        register_env = register_filters_fn

    asset_prefix = package_name.replace("-", "_").replace(".", "_")
    assets = _contract_assets(package_name, asset_prefix, asset_root, contract)
    runtime = _contract_runtime(package_name, contract.get("runtime"))

    logger.debug(
        "theme_library_provider_resolved",
        package=package_name,
        has_loader=loader is not None,
        has_asset_root=asset_root is not None,
        has_register_env=register_env is not None,
        contract_assets=len(assets),
        runtime=list(runtime),
    )

    return ThemeLibraryProvider(
        package=package_name,
        loader=loader,
        asset_root=asset_root,
        asset_prefix=asset_prefix,
        register_env=register_env,
        assets=assets,
        runtime=runtime,
    )


def resolve_theme_providers(
    site_root: Path,
    theme_chain: list[str],
) -> tuple[ThemeLibraryProvider, ...]:
    """Accumulate library providers from the theme inheritance chain.

    For each theme in the chain, reads its theme.toml for libraries,
    resolves each to a ThemeLibraryProvider, and deduplicates by package
    name (earlier theme in chain — i.e. child — wins).

    The resolved tuple is cached by ``(site_root, theme_chain)`` so the two
    independent build paths (asset discovery and Kida engine setup) — plus
    every shard worker thread under the #350 render backend — share one
    resolution instead of re-importing each library package per call. The
    result is a frozen+slots dataclass tuple, safe to share read-only across
    threads. The cache is RLock-backed (free-threading-safe under CPython
    3.14t) and registered for invalidation on full rebuild / config change.

    Args:
        site_root: Site root directory.
        theme_chain: Theme names from child to parent.

    Returns:
        Tuple of deduplicated ThemeLibraryProvider records.

    """
    # str() normalizes the key so Path-vs-str drift between callers cannot
    # split the cache; tuple() makes the (unhashable) chain list hashable.
    key = (str(site_root), tuple(theme_chain))
    return _provider_cache.get_or_set(
        key,
        lambda: _resolve_theme_providers_uncached(site_root, theme_chain),
    )


def _resolve_theme_providers_uncached(
    site_root: Path,
    theme_chain: list[str],
) -> tuple[ThemeLibraryProvider, ...]:
    """Resolve providers from the theme chain without consulting the cache."""
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


def clear_theme_provider_cache() -> None:
    """Clear the resolved theme-library provider cache."""
    _provider_cache.clear()


# Register cache for centralized invalidation (test cleanup + rebuilds).
# Mirrors registry.py's theme_cache: default invalidate_on={FULL_REBUILD} is
# augmented with CONFIG_CHANGED + BUILD_START so a theme.toml `libraries` edit
# in a long-lived dev-server/incremental process re-resolves providers.
try:
    from bengal.utils.cache_registry import InvalidationReason, register_cache

    register_cache(
        "theme_provider_cache",
        clear_theme_provider_cache,
        invalidate_on={
            InvalidationReason.FULL_REBUILD,
            InvalidationReason.CONFIG_CHANGED,
            InvalidationReason.BUILD_START,
        },
    )
except ImportError:
    # Cache registry not available (shouldn't happen in normal usage).
    pass


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
        if p.asset_root is not None and p.asset_root.exists() and not p.assets
    ]


def get_provider_assets(
    providers: tuple[ThemeLibraryProvider, ...],
) -> tuple[LibraryAsset, ...]:
    """Return explicit library assets declared by provider contracts."""
    return tuple(asset for provider in providers for asset in provider.assets)


def _normalize_contract(package_name: str, contract_raw: Any) -> dict[str, Any]:
    """Normalize get_library_contract() output into a plain dict."""
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if contract_raw is None:
        return {}
    if not isinstance(contract_raw, Mapping):
        raise BengalConfigError(
            f"Theme library '{package_name}': get_library_contract() returned "
            f"{type(contract_raw).__name__}, expected a mapping",
            code=ErrorCode.C003,
            suggestion=(
                f"Change '{package_name}.get_library_contract()' to return a dict-like "
                "contract with optional assets, runtime, loader, and asset_root fields."
            ),
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(contract_raw).__name__,
            ),
        )
    return dict(contract_raw)


def _check_contract_version(package_name: str, raw_version: Any) -> None:
    """Reject a library built against a contract Bengal cannot read.

    Libraries declare ``contract_version`` (an integer) to pin the contract
    schema revision they target. A library that omits it is treated as the v1
    convention contract (backwards compatible). A library declaring a version
    NEWER than this Bengal build understands is rejected here, at provider
    resolution, with an actionable BengalConfigError -- never mid-render.
    """
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if raw_version is None:
        return
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise BengalConfigError(
            f"Theme library '{package_name}': contract_version must be an integer, "
            f"got {type(raw_version).__name__}",
            code=ErrorCode.C004,
            suggestion=(
                "Return contract_version as a plain integer (e.g. contract_version=1) "
                "from get_library_contract()."
            ),
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(raw_version).__name__,
            ),
        )
    if raw_version > SUPPORTED_CONTRACT_VERSION:
        raise BengalConfigError(
            f"Theme library '{package_name}' targets contract version {raw_version}, "
            f"but this Bengal build supports up to {SUPPORTED_CONTRACT_VERSION}",
            code=ErrorCode.C003,
            suggestion=(
                f"Upgrade Bengal so it understands theme-library contract version "
                f"{raw_version}, or install a build of '{package_name}' that targets "
                f"contract version {SUPPORTED_CONTRACT_VERSION} or lower."
            ),
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
            ),
        )


def _check_requirements(package_name: str, raw_requires: Any) -> None:
    """Validate the library's declared version requirements at build start.

    A contract may declare ``requires`` as a mapping of distribution name to a
    PEP 440 version specifier, e.g. ``{"kida": ">=0.9.0"}``. For each entry,
    Bengal reads the INSTALLED version of the underlying distribution and
    verifies it satisfies the specifier. A missing distribution or a skewed
    version fails here with a BengalConfigError, instead of an ImportError or a
    missing-symbol crash on the first rendered page.
    """
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as installed_version

    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version

    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if raw_requires is None:
        return
    if not isinstance(raw_requires, Mapping):
        raise BengalConfigError(
            f"Theme library '{package_name}': requires must be a mapping of "
            f"distribution name to version specifier, got {type(raw_requires).__name__}",
            code=ErrorCode.C004,
            suggestion=(
                "Return requires as a dict like {'kida': '>=0.9.0'} from get_library_contract()."
            ),
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(raw_requires).__name__,
            ),
        )

    for req_name, spec_raw in raw_requires.items():
        if not isinstance(req_name, str) or not req_name:
            raise BengalConfigError(
                f"Theme library '{package_name}': requires keys must be non-empty "
                f"distribution names",
                code=ErrorCode.C004,
                suggestion="Use distribution names as keys, e.g. {'kida': '>=0.9.0'}.",
                debug_payload=_theme_library_debug_payload(
                    package_name, hook_name="get_library_contract"
                ),
            )
        if not isinstance(spec_raw, str):
            raise BengalConfigError(
                f"Theme library '{package_name}': requires['{req_name}'] must be a "
                f"version specifier string, got {type(spec_raw).__name__}",
                code=ErrorCode.C004,
                suggestion="Use a PEP 440 specifier string, e.g. '>=0.9.0,<1.0'.",
                debug_payload=_theme_library_debug_payload(
                    package_name,
                    hook_name="get_library_contract",
                    returned_type=type(spec_raw).__name__,
                ),
            )

        try:
            specifier = SpecifierSet(spec_raw)
        except InvalidSpecifier as e:
            raise BengalConfigError(
                f"Theme library '{package_name}': requires['{req_name}'] is not a "
                f"valid version specifier: {spec_raw!r}",
                code=ErrorCode.C003,
                suggestion="Use a PEP 440 specifier string, e.g. '>=0.9.0,<1.0'.",
                debug_payload=_theme_library_debug_payload(
                    package_name, hook_name="get_library_contract"
                ),
            ) from e

        dist_name = _REQUIREMENT_DISTRIBUTIONS.get(req_name, req_name)
        try:
            found = installed_version(dist_name)
        except PackageNotFoundError as e:
            raise BengalConfigError(
                f"Theme library '{package_name}' requires '{dist_name}' {spec_raw}, "
                f"but '{dist_name}' is not installed",
                code=ErrorCode.C003,
                suggestion=(
                    f"Install '{dist_name}{spec_raw}' in the build environment, or "
                    f"install '{package_name}' via its Bengal extra so the pin is "
                    "resolved for you."
                ),
                debug_payload=_theme_library_debug_payload(package_name),
            ) from e

        try:
            satisfied = Version(found) in specifier
        except InvalidVersion:
            # An unparseable installed version is treated as a mismatch rather
            # than crashing the guard itself.
            satisfied = False
        if not satisfied:
            raise BengalConfigError(
                f"Theme library '{package_name}' requires '{dist_name}' {spec_raw}, "
                f"but version {found} is installed",
                code=ErrorCode.C003,
                suggestion=(
                    f"Upgrade or downgrade '{dist_name}' to a version matching "
                    f"{spec_raw}, e.g. `uv pip install '{dist_name}{spec_raw}'`."
                ),
                debug_payload=_theme_library_debug_payload(package_name),
            )


def _normalize_asset_root(
    package_name: str,
    raw_root: Any,
    *,
    hook_name: str = "get_library_contract",
) -> Path | None:
    """Normalize a provider asset root to Path, preserving absent roots."""
    from pathlib import Path as _Path

    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if raw_root is None:
        return None
    try:
        return _Path(raw_root)
    except TypeError as e:
        msg = (
            f"Theme library '{package_name}': {hook_name} returned "
            f"{type(raw_root).__name__} for asset root, expected a path-like object"
        )
        raise BengalConfigError(
            msg,
            code=ErrorCode.C003,
            suggestion=(
                f"Change '{package_name}.{hook_name}()' to provide a str or Path asset root, "
                "or omit the asset root if the library has no static assets."
            ),
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name=hook_name,
                returned_type=type(raw_root).__name__,
            ),
        ) from e


def _contract_assets(
    package_name: str,
    asset_prefix: str,
    asset_root: Path | None,
    contract: Mapping[str, Any],
) -> tuple[LibraryAsset, ...]:
    """Normalize explicit provider asset declarations."""
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    default_mode = str(contract.get("mode") or "link")
    if default_mode not in _ASSET_MODES:
        raise BengalConfigError(
            f"Theme library '{package_name}': asset mode '{default_mode}' is invalid",
            code=ErrorCode.C003,
            suggestion="Use one of: bundle, link, none.",
            debug_payload=_theme_library_debug_payload(
                package_name, hook_name="get_library_contract"
            ),
        )

    raw_assets = list(_iter_contract_asset_entries(contract))
    if not raw_assets:
        return ()
    if asset_root is None:
        raise BengalConfigError(
            f"Theme library '{package_name}' declares assets but has no asset root",
            code=ErrorCode.C003,
            suggestion=(
                f"Return 'asset_root' from '{package_name}.get_library_contract()' or "
                "provide a static_path() hook."
            ),
            debug_payload=_theme_library_debug_payload(
                package_name, hook_name="get_library_contract"
            ),
        )

    assets: list[LibraryAsset] = []
    seen_logical: dict[Path, tuple[str, str]] = {}
    for entry in raw_assets:
        path_raw: Any
        output_raw: Any
        mode = default_mode
        asset_type = ""
        if isinstance(entry, Mapping):
            path_raw = entry.get("path") or entry.get("src") or entry.get("source")
            output_raw = entry.get("output") or entry.get("logical_path") or path_raw
            mode = str(entry.get("mode") or mode)
            asset_type = str(entry.get("type") or entry.get("kind") or "")
            tag_attrs = _contract_tag_attrs(package_name, entry)
        else:
            path_raw = entry
            output_raw = entry
            tag_attrs = ()

        if not path_raw:
            raise BengalConfigError(
                f"Theme library '{package_name}' has a library asset without a path",
                code=ErrorCode.C003,
                suggestion="Give each library asset a non-empty path.",
                debug_payload=_theme_library_debug_payload(
                    package_name,
                    hook_name="get_library_contract",
                ),
            )
        if mode not in _ASSET_MODES:
            raise BengalConfigError(
                f"Theme library '{package_name}': asset mode '{mode}' is invalid",
                code=ErrorCode.C003,
                suggestion="Use one of: bundle, link, none.",
                debug_payload=_theme_library_debug_payload(
                    package_name,
                    hook_name="get_library_contract",
                ),
            )

        source_path = _normalize_contract_path(
            package_name,
            path_raw,
            field_name="path",
            allow_absolute=True,
        )
        if not source_path.is_absolute():
            source_path = asset_root / source_path
            contract_path = Path(path_raw)
        else:
            contract_path = Path(source_path.name)
        output_path = _normalize_contract_path(
            package_name,
            output_raw,
            field_name="output",
            allow_absolute=False,
        )
        logical_path = Path(asset_prefix) / output_path
        if not asset_type:
            asset_type = _asset_type_from_path(source_path)
        previous = seen_logical.get(logical_path)
        if previous is not None:
            previous_mode, previous_type = previous
            if mode != "bundle" or previous_mode != "bundle" or asset_type != previous_type:
                raise BengalConfigError(
                    f"Theme library '{package_name}' declares duplicate asset output "
                    f"'{logical_path.as_posix()}'",
                    code=ErrorCode.C003,
                    suggestion=(
                        "Use unique output paths, or use bundle mode for every asset "
                        "that should concatenate into the same output file."
                    ),
                    debug_payload=_theme_library_debug_payload(
                        package_name,
                        hook_name="get_library_contract",
                    ),
                )
        else:
            seen_logical[logical_path] = (mode, asset_type)
        assets.append(
            LibraryAsset(
                source_path=source_path,
                logical_path=logical_path,
                asset_type=asset_type,
                mode=mode,
                package=package_name,
                contract_path=contract_path,
                tag_attrs=tag_attrs,
            )
        )
    return tuple(assets)


def _normalize_contract_path(
    package_name: str,
    raw_path: Any,
    *,
    field_name: str,
    allow_absolute: bool,
) -> Path:
    """Normalize a path-like contract field and reject ambiguous output paths."""
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if isinstance(raw_path, str) and not raw_path.strip():
        raw_path = None
    if raw_path is None:
        raise BengalConfigError(
            f"Theme library '{package_name}' has a library asset without a {field_name}",
            code=ErrorCode.C003,
            suggestion=f"Give each library asset a non-empty {field_name}.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(raw_path).__name__,
            ),
        )

    try:
        path = Path(raw_path)
    except TypeError as e:
        raise BengalConfigError(
            f"Theme library '{package_name}' asset {field_name} must be path-like, "
            f"got {type(raw_path).__name__}",
            code=ErrorCode.C003,
            suggestion=f"Use a string or pathlib.Path for asset {field_name}.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(raw_path).__name__,
            ),
        ) from e
    except ValueError as e:
        raise BengalConfigError(
            f"Theme library '{package_name}' asset {field_name} must be path-like, "
            f"got {type(raw_path).__name__}",
            code=ErrorCode.C003,
            suggestion=f"Use a string or pathlib.Path for asset {field_name}.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(raw_path).__name__,
            ),
        ) from e

    if path == Path("."):
        raise BengalConfigError(
            f"Theme library '{package_name}' has an empty asset {field_name}",
            code=ErrorCode.C003,
            suggestion=f"Give each library asset a non-empty {field_name}.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
            ),
        )
    if not allow_absolute and path.is_absolute():
        raise BengalConfigError(
            f"Theme library '{package_name}' asset {field_name} must be relative: {path}",
            code=ErrorCode.C003,
            suggestion="Use a relative output path so Bengal can namespace emitted assets.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
            ),
        )
    if ".." in path.parts:
        raise BengalConfigError(
            f"Theme library '{package_name}' asset {field_name} must not contain '..': {path}",
            code=ErrorCode.C003,
            suggestion="Use a path inside the library asset namespace.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
            ),
        )
    return path


def _contract_tag_attrs(
    package_name: str,
    entry: Mapping[str, Any],
) -> tuple[tuple[str, str | bool], ...]:
    """Normalize optional HTML attributes for provider-rendered asset tags."""
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    raw_attrs = entry.get("attributes", entry.get("attrs"))
    attrs: dict[str, str | bool] = {}
    if raw_attrs is not None:
        if not isinstance(raw_attrs, Mapping):
            raise BengalConfigError(
                f"Theme library '{package_name}' asset attributes must be a mapping",
                code=ErrorCode.C003,
                suggestion="Use attributes = {'defer': True, 'crossorigin': 'anonymous'}.",
                debug_payload=_theme_library_debug_payload(
                    package_name,
                    hook_name="get_library_contract",
                    returned_type=type(raw_attrs).__name__,
                ),
            )
        for raw_name, raw_value in raw_attrs.items():
            attrs[_normalize_attribute_name(package_name, raw_name)] = _normalize_attribute_value(
                package_name, raw_value
            )

    for bool_attr in ("async", "defer", "nomodule"):
        if bool_attr in entry and bool(entry[bool_attr]):
            attrs[bool_attr] = True
    if entry.get("module"):
        attrs["type"] = "module"
    if media := entry.get("media"):
        attrs["media"] = _normalize_attribute_value(package_name, media)

    for reserved in ("href", "src"):
        if reserved in attrs:
            raise BengalConfigError(
                f"Theme library '{package_name}' asset attributes must not set '{reserved}'",
                code=ErrorCode.C003,
                suggestion=(
                    "Use path/output for asset locations; Bengal owns href/src so "
                    "fingerprinted URLs stay correct."
                ),
                debug_payload=_theme_library_debug_payload(
                    package_name,
                    hook_name="get_library_contract",
                ),
            )
    return tuple(attrs.items())


def _normalize_attribute_name(package_name: str, raw_name: Any) -> str:
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if not isinstance(raw_name, str) or not raw_name:
        raise BengalConfigError(
            f"Theme library '{package_name}' asset attribute names must be non-empty strings",
            code=ErrorCode.C003,
            suggestion="Use HTML attribute names such as defer, media, integrity, or data-*.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(raw_name).__name__,
            ),
        )
    if not all(ch.isalnum() or ch in "-_:." for ch in raw_name):
        raise BengalConfigError(
            f"Theme library '{package_name}' asset attribute name is invalid: {raw_name}",
            code=ErrorCode.C003,
            suggestion="Use plain HTML attribute names without whitespace or quotes.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
            ),
        )
    return raw_name


def _normalize_attribute_value(package_name: str, raw_value: Any) -> str | bool:
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        return raw_value
    raise BengalConfigError(
        f"Theme library '{package_name}' asset attribute values must be strings or booleans",
        code=ErrorCode.C003,
        suggestion="Use True for boolean HTML attributes or a string for valued attributes.",
        debug_payload=_theme_library_debug_payload(
            package_name,
            hook_name="get_library_contract",
            returned_type=type(raw_value).__name__,
        ),
    )


def _iter_contract_asset_entries(contract: Mapping[str, Any]) -> Sequence[Any]:
    """Yield explicit asset declarations from compact or grouped contract fields."""
    assets = contract.get("assets")
    if assets is not None:
        if isinstance(assets, Sequence) and not isinstance(assets, (str, bytes)):
            return assets
        return [assets]

    grouped: list[dict[str, Any]] = []
    for kind, field_name in (("css", "css"), ("javascript", "js")):
        values = contract.get(field_name)
        if values is None:
            continue
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            values = [values]
        for value in values:
            if isinstance(value, Mapping):
                item = dict(value)
                item.setdefault("type", kind)
                grouped.append(item)
            else:
                grouped.append({"path": value, "type": kind})
    return grouped


def _contract_runtime(package_name: str, runtime_raw: Any) -> tuple[str, ...]:
    """Normalize optional runtime metadata from a provider contract."""
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    if runtime_raw is None:
        return ()
    if isinstance(runtime_raw, str):
        return (runtime_raw,)
    if isinstance(runtime_raw, bytes) or not isinstance(runtime_raw, Sequence):
        raise BengalConfigError(
            f"Theme library '{package_name}': runtime must be a string or list of strings",
            code=ErrorCode.C003,
            suggestion="Use runtime = ['alpine'] style metadata in the library contract.",
            debug_payload=_theme_library_debug_payload(
                package_name,
                hook_name="get_library_contract",
                returned_type=type(runtime_raw).__name__,
            ),
        )
    runtime: list[str] = []
    for item in runtime_raw:
        if not isinstance(item, str):
            raise BengalConfigError(
                f"Theme library '{package_name}': runtime entries must be strings",
                code=ErrorCode.C003,
                suggestion="Use runtime = ['alpine'] style metadata in the library contract.",
                debug_payload=_theme_library_debug_payload(
                    package_name,
                    hook_name="get_library_contract",
                    returned_type=type(item).__name__,
                ),
            )
        if item:
            runtime.append(item)
    return tuple(runtime)


def _asset_type_from_path(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".css":
        return "css"
    if ext == ".js":
        return "javascript"
    if ext in {".woff", ".woff2", ".ttf", ".otf", ".eot"}:
        return "font"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".avif"}:
        return "image"
    return "other"


def _probe_hook(package_name: str, module: Any, hook_name: str) -> Any | None:
    """Call a convention hook on a library module, returning None if absent."""
    from bengal.errors import ErrorCode
    from bengal.errors.exceptions import BengalConfigError

    fn = getattr(module, hook_name, None)
    if fn is None or not callable(fn):
        return None
    try:
        return fn()
    except Exception as e:
        msg = f"Theme library '{package_name}': {hook_name}() failed: {e}"
        raise BengalConfigError(
            msg,
            code=ErrorCode.C003,
            suggestion=(
                f"Fix '{package_name}.{hook_name}()' or remove the hook if the "
                "library does not provide that capability."
            ),
            debug_payload=_theme_library_debug_payload(package_name, hook_name=hook_name),
        ) from e
