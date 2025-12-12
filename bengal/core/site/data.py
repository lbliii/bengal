"""
Data loading mixin for Site.

Provides methods for loading data files from the data/ directory into site.data.

Related Modules:
    - bengal.core.site.core: Main Site dataclass using this mixin
    - bengal.utils.dotdict: DotDict for dot-notation access
    - bengal.utils.file_io: Data file loading utilities
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.core.diagnostics import emit as emit_diagnostic

if TYPE_CHECKING:
    from bengal.utils.dotdict import DotDict


class DataLoadingMixin:
    """
    Mixin providing data directory loading methods.

    Requires these attributes on the host class:
        - root_path: Path
    """

    # Type hints for mixin attributes (provided by host class)
    root_path: Path

    def _load_data_directory(self) -> DotDict:
        """
        Load all data files from the data/ directory into site.data.

        Supports YAML, JSON, and TOML files. Files are loaded into a nested
        structure based on their path in the data/ directory.

        Example:
            data/resume.yaml → site.data.resume
            data/team/members.json → site.data.team.members

        Returns:
            DotDict with loaded data accessible via dot notation
        """
        from bengal.utils.dotdict import DotDict, wrap_data
        from bengal.utils.file_io import load_data_file

        data_dir = self.root_path / "data"

        if not data_dir.exists():
            emit_diagnostic(self, "debug", "data_directory_not_found", path=str(data_dir))
            return DotDict()

        emit_diagnostic(self, "debug", "loading_data_directory", path=str(data_dir))

        data: dict[str, Any] = {}
        supported_extensions = [".json", ".yaml", ".yml", ".toml"]

        for file_path in data_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix not in supported_extensions:
                continue

            relative = file_path.relative_to(data_dir)
            parts = list(relative.with_suffix("").parts)

            try:
                content = load_data_file(
                    file_path, on_error="return_empty", caller="site_data_loader"
                )

                current = data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                current[parts[-1]] = content

                # Validate tracks.yaml structure if this is tracks data
                if parts[-1] == "tracks" and isinstance(content, dict):
                    self._validate_tracks_structure(content)

                emit_diagnostic(
                    self,
                    "debug",
                    "data_file_loaded",
                    file=str(relative),
                    key=".".join(parts),
                    size=len(str(content)) if content else 0,
                )

            except Exception as e:
                emit_diagnostic(
                    self,
                    "warning",
                    "data_file_load_failed",
                    file=str(relative),
                    error=str(e),
                    error_type=type(e).__name__,
                )

        wrapped_data: DotDict = wrap_data(data)

        if data:
            emit_diagnostic(
                self,
                "debug",
                "data_directory_loaded",
                files_loaded=len(list(data_dir.rglob("*.*"))),
                top_level_keys=list(data.keys()) if isinstance(data, dict) else [],
            )

        return wrapped_data

    def _validate_tracks_structure(self, tracks_data: dict[str, Any]) -> None:
        """
        Validate tracks.yaml structure during data loading.

        Logs warnings for invalid tracks but doesn't fail the build.
        This provides early feedback during development.

        Args:
            tracks_data: Dictionary loaded from tracks.yaml
        """
        if not isinstance(tracks_data, dict):
            emit_diagnostic(
                self,
                "warning",
                "tracks.yaml root must be a dictionary",
                event="tracks_invalid_structure",
            )
            return

        for track_id, track in tracks_data.items():
            if not isinstance(track, dict):
                emit_diagnostic(
                    self,
                    "warning",
                    f"Track '{track_id}' must be a dictionary",
                    event="track_invalid_structure",
                    track_id=track_id,
                )
                continue

            # Check required fields
            if "items" not in track:
                emit_diagnostic(
                    self,
                    "warning",
                    f"Track '{track_id}' is missing required 'items' field",
                    event="track_missing_items",
                    track_id=track_id,
                )
                continue

            if not isinstance(track["items"], list):
                emit_diagnostic(
                    self,
                    "warning",
                    f"Track '{track_id}' has 'items' field that is not a list",
                    event="track_items_not_list",
                    track_id=track_id,
                )
                continue

            # Warn about empty tracks (may be intentional, but worth noting)
            if len(track["items"]) == 0:
                emit_diagnostic(
                    self,
                    "debug",
                    f"Track '{track_id}' has no items",
                    event="track_empty_items",
                    track_id=track_id,
                )
