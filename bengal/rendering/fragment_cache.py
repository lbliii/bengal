"""Bengal-aware wrappers for template fragment caches."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from bengal.rendering.assets import AssetSiteLike


class AssetManifestFragmentCache:
    """Namespace Kida fragment cache keys by the active asset manifest revision."""

    __slots__ = ("_cache", "_site")

    def __init__(self, cache: Any, site: AssetSiteLike) -> None:
        self._cache = cache
        self._site = site

    def _key(self, key: str) -> str:
        from bengal.rendering.assets import get_asset_manifest_revision

        revision = get_asset_manifest_revision(self._site)
        if revision is None:
            return key
        return f"asset-manifest:{revision}:{key}"

    def get(self, key: str) -> str | None:
        return self._cache.get(self._key(key))

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], str] | Callable[[str], str],
        *,
        pass_key: bool = False,
        ttl: float | None = None,
    ) -> str:
        namespaced_key = self._key(key)
        if pass_key:
            key_factory = cast("Callable[[str], str]", factory)
            return self._cache.get_or_set(
                namespaced_key,
                lambda _namespaced_key: key_factory(key),
                pass_key=True,
                ttl=ttl,
            )
        return self._cache.get_or_set(
            namespaced_key,
            factory,
            ttl=ttl,
        )

    def set(self, key: str, value: str, *, ttl: float | None = None) -> None:
        self._cache.set(self._key(key), value, ttl=ttl)

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> dict[str, Any]:
        return self._cache.stats()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cache, name)
