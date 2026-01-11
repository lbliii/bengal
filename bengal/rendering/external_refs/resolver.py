"""
External reference resolver for Bengal SSG.

Resolves [[ext:project:target]] references using three-tier resolution:
1. URL Templates (Instant, Offline)
2. Bengal Index (Cached)
3. Graceful Fallback

Design Goals (from RFC):
    - Offline by default — Most links resolve without network
    - Builds never fail — External issues = warnings only
    - Progressive enhancement — Start simple, add features as needed
    - Bengal-native — Own format, not Sphinx compatibility

Example:
    >>> resolver = ExternalRefResolver(config)
    >>> html = resolver.resolve("python", "pathlib.Path")
    '<a href="https://docs.python.org/3/library/pathlib.html#Path" class="extref">Path</a>'

    >>> html = resolver.resolve("kida", "Markup", text="Kida Markup")
    '<a href="https://kida.dev/api/python/kida/#Markup" class="extref">Kida Markup</a>'

See: plan/rfc-external-references.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING, Any

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from bengal.config.accessor import Config

logger = get_logger(__name__)


@dataclass
class ExternalRefEntry:
    """An entry from an external xref.json index."""

    type: str  # page, class, function, method, module, cli, endpoint
    path: str  # URL path (e.g., /api/python/kida/#Markup)
    title: str  # Display title
    summary: str | None = None  # Optional description


@dataclass
class UnresolvedRef:
    """Tracks an unresolved external reference for health checks."""

    project: str
    target: str
    source_file: Path | None = None
    line: int | None = None


@dataclass
class ExternalRefResolver:
    """
    Resolver for external documentation references.

    Implements three-tier resolution:
    1. URL Templates - Instant, offline pattern matching
    2. Bengal Index - Cached xref.json from other Bengal sites
    3. Graceful Fallback - Render as code + emit warning

    Attributes:
        config: Site configuration
        templates: URL templates for common documentation sites
        indexes: Cached Bengal indexes
        unresolved: List of unresolved references for health checks

    Example:
        >>> resolver = ExternalRefResolver(config)
        >>> resolver.resolve("python", "pathlib.Path")
        '<a href="..." class="extref">Path</a>'
    """

    config: Config | dict[str, Any]
    templates: dict[str, str] = field(default_factory=dict)
    indexes: dict[str, dict[str, ExternalRefEntry]] = field(default_factory=dict)
    unresolved: list[UnresolvedRef] = field(default_factory=list)
    _cache: IndexCache | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize from config."""
        external_refs = self._get_external_refs_config()

        # Load URL templates
        self.templates = dict(external_refs.get("templates", {}))

        # Initialize index cache
        cache_dir = external_refs.get("cache_dir", ".bengal/cache/external_refs")
        default_cache_days = external_refs.get("default_cache_days", 7)
        self._cache = IndexCache(
            cache_dir=Path(cache_dir),
            default_cache_days=default_cache_days,
        )

        # Pre-load configured indexes
        for index_config in external_refs.get("indexes", []):
            name = index_config.get("name", "")
            if name:
                # Indexes are loaded lazily on first use
                pass

    def _get_external_refs_config(self) -> dict[str, Any]:
        """Get external_refs config section."""
        if hasattr(self.config, "get"):
            config = self.config.get("external_refs", {})
        else:
            config = self.config.get("external_refs", {}) if isinstance(self.config, dict) else {}

        if isinstance(config, bool):
            return {"enabled": config}
        return config or {}

    def resolve(
        self,
        project: str,
        target: str,
        text: str | None = None,
        source_file: Path | None = None,
        line: int | None = None,
    ) -> str:
        """
        Resolve an external reference to HTML.

        Tries resolution in order:
        1. URL template (instant, offline)
        2. Bengal index (cached)
        3. Graceful fallback (code + warning)

        Args:
            project: Project identifier (e.g., "python", "kida")
            target: Target within project (e.g., "pathlib.Path", "Markup")
            text: Optional custom link text
            source_file: Source file for error tracking
            line: Line number for error tracking

        Returns:
            HTML string - either a link or a fallback code element
        """
        # Tier 1: URL template
        if url := self._resolve_template(project, target):
            display_text = text or self._extract_display_name(target)
            return f'<a href="{url}" class="extref">{display_text}</a>'

        # Tier 2: Bengal index
        if entry := self._resolve_index(project, target):
            display_text = text or entry.title
            title_attr = f' title="{entry.summary}"' if entry.summary else ""
            return f'<a href="{entry.path}" class="extref"{title_attr}>{display_text}</a>'

        # Tier 3: Graceful fallback
        logger.warning(
            "unresolved_external_ref",
            project=project,
            target=target,
            source_file=str(source_file) if source_file else None,
            line=line,
            suggestion=f"Add '{project}' to external_refs.templates or external_refs.indexes",
        )

        self.unresolved.append(
            UnresolvedRef(
                project=project,
                target=target,
                source_file=source_file,
                line=line,
            )
        )

        display_text = text or target
        return f'<code class="extref extref-unresolved">ext:{project}:{display_text}</code>'

    def can_resolve(self, project: str, target: str) -> bool:
        """
        Check if a reference can be resolved.

        Useful for conditional rendering in templates.

        Args:
            project: Project identifier
            target: Target within project

        Returns:
            True if resolvable via template or index
        """
        if self._resolve_template(project, target):
            return True
        return bool(self._resolve_index(project, target))

    def _resolve_template(self, project: str, target: str) -> str | None:
        """
        Resolve using URL template. O(1), no network.

        Args:
            project: Project identifier (e.g., "python")
            target: Target (e.g., "pathlib.Path")

        Returns:
            URL string or None if no template matches
        """
        template = self.templates.get(project)
        if not template:
            return None

        return resolve_template(template, target)

    def _resolve_index(self, project: str, target: str) -> ExternalRefEntry | None:
        """
        Resolve using Bengal index. Uses cache.

        Args:
            project: Project identifier
            target: Target within project

        Returns:
            ExternalRefEntry or None if not found
        """
        # Check if we have this index loaded
        if project not in self.indexes:
            # Try to load from cache or fetch
            self._load_index(project)

        index = self.indexes.get(project, {})
        return index.get(target)

    def _load_index(self, project: str) -> None:
        """
        Load index for a project from cache or network.

        Args:
            project: Project identifier to load
        """
        external_refs = self._get_external_refs_config()

        # Find index config
        index_config = None
        for cfg in external_refs.get("indexes", []):
            if cfg.get("name") == project:
                index_config = cfg
                break

        if not index_config:
            # No index configured for this project
            self.indexes[project] = {}
            return

        url = index_config.get("url", "")
        cache_days = index_config.get("cache_days")

        if not url:
            self.indexes[project] = {}
            return

        headers = self._extract_headers(index_config)

        # Use cache to get index
        if self._cache:
            raw_index = self._cache.get(project, url, cache_days, headers=headers)
            if raw_index:
                self.indexes[project] = self._parse_index(raw_index)
            else:
                self.indexes[project] = {}
        else:
            self.indexes[project] = {}

    def _parse_index(self, raw_index: dict[str, Any]) -> dict[str, ExternalRefEntry]:
        """
        Parse raw xref.json into ExternalRefEntry objects.

        Args:
            raw_index: Raw JSON from xref.json

        Returns:
            Dictionary of entry key -> ExternalRefEntry
        """
        entries: dict[str, ExternalRefEntry] = {}

        # Get project base URL
        project_url = raw_index.get("project", {}).get("url", "")

        for key, entry_data in raw_index.get("entries", {}).items():
            path = entry_data.get("path", "")

            # Make path absolute if project URL is available
            if path and not path.startswith(("http://", "https://")) and project_url:
                path = project_url.rstrip("/") + path

            entries[key] = ExternalRefEntry(
                type=entry_data.get("type", "page"),
                path=path,
                title=entry_data.get("title", key),
                summary=entry_data.get("summary"),
            )

        return entries

    def _extract_headers(self, index_config: dict[str, Any]) -> dict[str, str] | None:
        """
        Extract HTTP headers for index fetching.

        Supports:
            - auth_header: "Header: value" or value (defaults to Authorization)
            - headers: dict of additional headers
        """
        headers: dict[str, str] = {}

        auth_header = index_config.get("auth_header")
        if isinstance(auth_header, str):
            if ":" in auth_header:
                key, val = auth_header.split(":", 1)
                headers[key.strip()] = val.strip()
            elif auth_header.strip():
                headers["Authorization"] = auth_header.strip()

        extra_headers = index_config.get("headers")
        if isinstance(extra_headers, dict):
            for key, val in extra_headers.items():
                if val:
                    headers[key] = str(val)

        return headers or None

    def _extract_display_name(self, target: str) -> str:
        """
        Extract display name from target.

        "pathlib.Path" -> "Path"
        "numpy.ndarray" -> "ndarray"

        Args:
            target: Full target string

        Returns:
            Short display name
        """
        if "." in target:
            return target.rsplit(".", 1)[-1]
        return target


def resolve_template(template: str, target: str) -> str:
    """
    Resolve URL template with target variables.

    Available variables:
        - {target}: Full target string (e.g., "pathlib.Path")
        - {module}: Module part (e.g., "pathlib")
        - {name}: Name part (e.g., "Path")
        - {name_lower}: Lowercase name (e.g., "path")

    Args:
        template: URL template string
        target: Target to resolve

    Returns:
        Expanded URL string

    Example:
        >>> resolve_template(
        ...     "https://docs.python.org/3/library/{module}.html#{name}",
        ...     "pathlib.Path"
        ... )
        'https://docs.python.org/3/library/pathlib.html#Path'
    """
    # Parse target: "pathlib.Path" → module="pathlib", name="Path"
    parts = target.rsplit(".", 1)
    module = parts[0] if len(parts) > 1 else target
    name = parts[-1]

    return template.format(
        target=target,
        module=module,
        name=name,
        name_lower=name.lower(),
    )


@dataclass
class IndexCache:
    """
    Cache for external reference indexes.

    Implements stale-while-revalidate pattern:
    - Fresh cache: Return immediately
    - Stale cache: Return immediately, refresh in background
    - No cache: Fetch synchronously (first time only)

    Attributes:
        cache_dir: Directory to store cached indexes
        default_cache_days: Default cache duration
    """

    cache_dir: Path
    default_cache_days: int = 7

    def get(
        self,
        project: str,
        url: str,
        max_age_days: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Get index from cache or fetch.

        Args:
            project: Project identifier (used as cache key)
            url: URL to fetch if not cached
            max_age_days: Max cache age (overrides default)

        Returns:
            Parsed JSON index or None if fetch failed
        """
        import json
        from datetime import datetime

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{project}.json"
        max_age = max_age_days if max_age_days is not None else self.default_cache_days

        # Check cache
        if cache_file.exists():
            try:
                age_seconds = datetime.now().timestamp() - cache_file.stat().st_mtime
                age_days = age_seconds / (24 * 60 * 60)

                cached = json.loads(cache_file.read_text(encoding="utf-8"))

                if age_days < max_age:
                    logger.debug(
                        "external_ref_cache_hit",
                        project=project,
                        age_days=round(age_days, 1),
                    )
                    return cached

                # Stale cache - use it but try to refresh in background
                logger.debug(
                    "external_ref_cache_stale",
                    project=project,
                    age_days=round(age_days, 1),
                    max_age_days=max_age,
                )
                Thread(
                    target=self._refresh_cache,
                    args=(project, url, cache_file, headers, max_age),
                    daemon=True,
                ).start()
                return cached

            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "external_ref_cache_read_error",
                    project=project,
                    error=str(e),
                )

        # No cache - fetch synchronously
        return self._fetch(project, url, cache_file, headers=headers)

    def _fetch(
        self,
        project: str,
        url: str,
        cache_file: Path,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch index from URL and cache.

        Args:
            project: Project identifier
            url: URL to fetch
            cache_file: Path to cache file

        Returns:
            Parsed JSON or None if fetch failed
        """
        import json

        # Check if URL is a local file path
        if url.startswith("file://") or not url.startswith(("http://", "https://")):
            return self._fetch_local(project, url, cache_file, headers=headers)

        try:
            import urllib.request

            logger.info(
                "external_ref_fetching",
                project=project,
                url=url,
            )

            request = urllib.request.Request(url, headers=headers or {})

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))

                    # Cache the result
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(
                        json.dumps(data, indent=2),
                        encoding="utf-8",
                    )

                    logger.info(
                        "external_ref_fetched",
                        project=project,
                        entries=len(data.get("entries", {})),
                    )
                    return data

        except Exception as e:
            logger.warning(
                "external_ref_fetch_failed",
                project=project,
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )

        return None

    def _fetch_local(
        self,
        project: str,
        url: str,
        cache_file: Path,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Load index from local file path.

        Args:
            project: Project identifier
            url: Local file path (with or without file:// prefix)
            cache_file: Path to cache file (unused for local)

        Returns:
            Parsed JSON or None if load failed
        """
        import json

        # Strip file:// prefix if present
        path_str = url.removeprefix("file://")
        path = Path(path_str)

        if not path.exists():
            logger.warning(
                "external_ref_local_not_found",
                project=project,
                path=str(path),
            )
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            logger.debug(
                "external_ref_local_loaded",
                project=project,
                path=str(path),
                entries=len(data.get("entries", {})),
            )
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "external_ref_local_error",
                project=project,
                path=str(path),
                error=str(e),
            )
            return None

    def _refresh_cache(
        self,
        project: str,
        url: str,
        cache_file: Path,
        headers: dict[str, str] | None,
        max_age_days: int,
    ) -> None:
        """
        Refresh cache in background for stale entries.
        """
        try:
            self._fetch(project, url, cache_file, headers=headers)
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(
                "external_ref_background_refresh_failed",
                project=project,
                url=url,
                error=str(e),
                max_age_days=max_age_days,
            )
