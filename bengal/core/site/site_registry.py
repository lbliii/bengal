"""
Site Registry Mixin - Config service, indexes, and content registry.

Provides lazy-initialized config_service, indexes, and registry for
thread-safe config access and O(1) content lookups.

See Also:
- bengal/core/site/__init__.py: Site class that uses this mixin
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bengal.core.diagnostics import emit as emit_diagnostic
from bengal.core.registry import ContentRegistry
from bengal.protocols.core import SiteLike
from bengal.services.config import ConfigService

if TYPE_CHECKING:
    from bengal.cache.query_index_registry import QueryIndexRegistry


class SiteRegistryMixin:
    """
    Mixin providing config service, indexes, and content registry.

    Handles:
    - config_service: Immutable ConfigService for thread-safe config access
    - indexes: QueryIndexRegistry for O(1) page lookups
    - registry: ContentRegistry for O(1) page/section lookups
    - _compute_config_hash: Config hash for cache invalidation
    """

    config: object
    root_path: object
    paths: object
    url_registry: object
    _config_service: ConfigService | None
    _config_hash: str | None
    _query_registry: QueryIndexRegistry | None
    _registry: ContentRegistry | None

    @property
    def config_service(self) -> ConfigService:
        """
        Immutable configuration service for thread-safe config access.

        Cost: O(1) — lazy init, then direct field read.
        """
        if self._config_service is None:
            self._config_service = ConfigService.from_config(self.config, self.root_path)
        return self._config_service

    def _compute_config_hash(self) -> None:
        """Compute and cache the configuration hash (backward compat)."""
        from bengal.config.hash import compute_config_hash

        self._config_hash = compute_config_hash(self.config)
        emit_diagnostic(
            self,
            "debug",
            "config_hash_computed",
            hash=self._config_hash[:8] if self._config_hash else "none",
        )

    @property
    def indexes(self) -> QueryIndexRegistry:
        """Access to query indexes for O(1) page lookups.

        Cost: O(1) — lazy init, then direct field read.
        """
        if self._query_registry is None:
            from bengal.cache.query_index_registry import QueryIndexRegistry

            self._query_registry = QueryIndexRegistry(cast(SiteLike, self), self.paths.indexes_dir)
        return self._query_registry

    @property
    def registry(self) -> ContentRegistry:
        """
        Content registry for O(1) page/section lookups.

        Cost: O(1) — lazy init, then direct field read.
        """
        if self._registry is None:
            self._registry = ContentRegistry()
            self._registry.set_root_path(self.root_path)
            self._registry.url_ownership = self.url_registry
        return self._registry
