"""Search backend contracts for generated search artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from bengal.errors import BengalConfigError, ErrorCode
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bengal.protocols import SiteLike


SUPPORTED_SEARCH_BACKENDS = frozenset({"lunr"})
logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SearchBackendConfig:
    """Resolved search backend configuration."""

    enabled: bool = True
    backend: str = "lunr"
    lunr: dict[str, Any] = field(default_factory=dict)

    @property
    def prebuilt_enabled(self) -> bool:
        """Whether this backend should emit prebuilt search artifacts."""
        return bool(self.lunr.get("prebuilt", True))


class SearchIndexBackend(Protocol):
    """Provider interface for search artifacts generated from index.json."""

    name: str

    def generate(
        self,
        index_paths: list[Path],
        timed_generate: Callable[[str, Callable[[], Path | None]], Path | None],
    ) -> list[str]:
        """Generate backend artifacts for the provided index.json files."""
        ...


def resolve_search_backend_config(config: dict[str, Any] | bool | None) -> SearchBackendConfig:
    """Resolve public search config into an explicit backend selection."""
    if config is False:
        return SearchBackendConfig(enabled=False)
    if config is True or config is None:
        return SearchBackendConfig()
    if not isinstance(config, dict):
        raise BengalConfigError(
            "Invalid search configuration: expected a table or boolean.",
            code=ErrorCode.C004,
            debug_payload={"value_type": type(config).__name__},
            suggestion="Set search.enabled to true/false or configure search as a table.",
        )

    enabled = bool(config.get("enabled", True))
    backend = str(config.get("backend", "lunr")).strip().lower()
    if backend not in SUPPORTED_SEARCH_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_SEARCH_BACKENDS))
        raise BengalConfigError(
            f"Unsupported search backend: {backend!r}.",
            code=ErrorCode.C003,
            debug_payload={"backend": backend, "supported": supported},
            suggestion=f"Use search.backend = 'lunr'. Supported backends: {supported}.",
        )

    lunr_config = config.get("lunr", {})
    if lunr_config is None:
        lunr_config = {}
    if not isinstance(lunr_config, dict):
        raise BengalConfigError(
            "Invalid search.lunr configuration: expected a table.",
            code=ErrorCode.C004,
            debug_payload={"value_type": type(lunr_config).__name__},
            suggestion="Configure Lunr options under search.lunr, or remove the key.",
        )

    return SearchBackendConfig(enabled=enabled, backend=backend, lunr=dict(lunr_config))


class LunrSearchBackend:
    """Generate Lunr-compatible search artifacts."""

    name = "lunr"

    def __init__(self, site: SiteLike, config: SearchBackendConfig) -> None:
        self.site = site
        self.config = config

    def generate(
        self,
        index_paths: list[Path],
        timed_generate: Callable[[str, Callable[[], Path | None]], Path | None],
    ) -> list[str]:
        """Generate prebuilt Lunr indexes alongside each index.json."""
        if not self.config.enabled or not self.config.prebuilt_enabled:
            return []

        from bengal.postprocess.output_formats.lunr_index_generator import LunrIndexGenerator

        lunr_gen = LunrIndexGenerator(self.site)
        if not lunr_gen.is_available():
            logger.debug(
                "lunr_prebuilt_skipped",
                reason="lunr package not installed",
            )
            return []

        generated = []
        for index_path in index_paths:
            lunr_path = timed_generate(
                "site_lunr_index",
                lambda index_path=index_path: lunr_gen.generate(index_path),
            )
            if lunr_path:
                generated.append("search-index.json")
        return generated


def create_search_backend(site: SiteLike, config: SearchBackendConfig) -> SearchIndexBackend:
    """Create the configured search backend adapter."""
    if config.backend == "lunr":
        return LunrSearchBackend(site, config)

    supported = ", ".join(sorted(SUPPORTED_SEARCH_BACKENDS))
    raise BengalConfigError(
        f"Unsupported search backend: {config.backend!r}.",
        code=ErrorCode.C003,
        debug_payload={"backend": config.backend, "supported": supported},
        suggestion=f"Use search.backend = 'lunr'. Supported backends: {supported}.",
    )
