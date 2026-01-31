"""
Data service - pure functions for data loading.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)

Replaces DataLoadingMixin with pure functions that load and
cache data files.

Key Principles:
- Pure functions: no hidden state
- Explicit dependencies: root_path passed explicitly
- Cacheable: same inputs → same outputs
- Thread-safe: no shared mutable state
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot


@dataclass(frozen=True, slots=True)
class DataSnapshot:
    """
    Frozen snapshot of loaded data files.

    Created once at build start, immutable during build.
    """

    # Nested data structure (like site.data)
    data: MappingProxyType[str, Any]

    # Source files that were loaded (for dependency tracking)
    source_files: frozenset[Path]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level data key."""
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Dict-style access."""
        return self.data[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self.data


@dataclass(frozen=True, slots=True)
class DataService:
    """
    Cached data loading service.

    Loads data files from data/ directory and provides
    cached access to the loaded data.

    Usage:
        >>> service = DataService.from_root(root_path)
        >>> resume = service.get("resume")
        >>> team = service.get("team.members")
    """

    root_path: Path
    snapshot: DataSnapshot

    @classmethod
    def from_root(cls, root_path: Path) -> DataService:
        """
        Create service by loading data from root_path/data/.

        Args:
            root_path: Site root path

        Returns:
            DataService with loaded data
        """
        snapshot = load_data_directory(root_path)
        return cls(root_path=root_path, snapshot=snapshot)

    @classmethod
    def from_site_snapshot(cls, snapshot: SiteSnapshot) -> DataService:
        """
        Create service from SiteSnapshot.

        Args:
            snapshot: Site snapshot (uses root_path)

        Returns:
            DataService with loaded data
        """
        return cls.from_root(snapshot.root_path)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get data by dot-notation key.

        Args:
            key: Dot-notation key (e.g., "team.members")
            default: Default value if not found

        Returns:
            Data value or default
        """
        return get_data(self.snapshot, key, default)

    def get_file(self, relative_path: str) -> Any:
        """
        Get data from a specific file.

        Args:
            relative_path: Path relative to data/ (e.g., "resume.yaml")

        Returns:
            Loaded file content or None
        """
        file_path = self.root_path / "data" / relative_path
        return get_data_file(file_path)


def load_data_directory(root_path: Path) -> DataSnapshot:
    """
    Load all data files from the data/ directory.

    Pure function: loads files, returns frozen snapshot.

    Supports YAML, JSON, and TOML files. Files are loaded into
    a nested structure based on their path in the data/ directory.

    Example:
        data/resume.yaml → result["resume"]
        data/team/members.json → result["team"]["members"]

    Args:
        root_path: Site root path

    Returns:
        DataSnapshot with loaded data
    """
    data_dir = root_path / "data"

    if not data_dir.exists():
        return DataSnapshot(
            data=MappingProxyType({}),
            source_files=frozenset(),
        )

    data: dict[str, Any] = {}
    source_files: set[Path] = set()
    supported_extensions = {".json", ".yaml", ".yml", ".toml"}

    for file_path in data_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix not in supported_extensions:
            continue

        relative = file_path.relative_to(data_dir)
        parts = list(relative.with_suffix("").parts)

        try:
            content = _load_data_file_content(file_path)

            # Build nested structure
            current = data
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = content
            source_files.add(file_path)

        except Exception:
            # Skip files that fail to load
            pass

    return DataSnapshot(
        data=_freeze_dict(data),
        source_files=frozenset(source_files),
    )


def get_data(snapshot: DataSnapshot, key: str, default: Any = None) -> Any:
    """
    Get data by dot-notation key.

    Pure function.

    Args:
        snapshot: DataSnapshot
        key: Dot-notation key (e.g., "team.members")
        default: Default value if not found

    Returns:
        Data value or default
    """
    parts = key.split(".")
    current: Any = snapshot.data

    for part in parts:
        if isinstance(current, (dict, MappingProxyType)):
            if part in current:
                current = current[part]
            else:
                return default
        else:
            return default

    return current


def get_data_file(file_path: Path) -> Any:
    """
    Load a specific data file.

    Pure function.

    Args:
        file_path: Path to data file

    Returns:
        Loaded content or None if load fails
    """
    if not file_path.exists():
        return None
    return _load_data_file_content(file_path)


def _load_data_file_content(file_path: Path) -> Any:
    """Load content from a data file."""
    try:
        from bengal.utils.io.file_io import load_data_file
        return load_data_file(file_path, on_error="return_empty", caller="data_service")
    except ImportError:
        # Fallback for standalone usage
        suffix = file_path.suffix.lower()

        if suffix == ".json":
            import json
            return json.loads(file_path.read_text())
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml
                return yaml.safe_load(file_path.read_text())
            except ImportError:
                return None
        elif suffix == ".toml":
            try:
                import tomllib
                return tomllib.loads(file_path.read_text())
            except ImportError:
                try:
                    import tomli
                    return tomli.loads(file_path.read_text())
                except ImportError:
                    return None

        return None


def _freeze_dict(d: dict[str, Any]) -> MappingProxyType[str, Any]:
    """Recursively freeze a dictionary."""
    result: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _freeze_dict(v)
        elif isinstance(v, list):
            result[k] = tuple(_freeze_item(item) for item in v)
        else:
            result[k] = v
    return MappingProxyType(result)


def _freeze_item(item: Any) -> Any:
    """Freeze a single item (dict → MappingProxyType, list → tuple)."""
    if isinstance(item, dict):
        return _freeze_dict(item)
    elif isinstance(item, list):
        return tuple(_freeze_item(i) for i in item)
    return item
