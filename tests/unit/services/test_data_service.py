"""
Unit tests for DataService.

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 4: Service Extraction)
"""

from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.services.data import (
    DataService,
    DataSnapshot,
    get_data,
    load_data_directory,
)


class TestDataSnapshot:
    """Tests for DataSnapshot."""

    def test_create_empty_snapshot(self) -> None:
        """DataSnapshot can be created empty."""
        snapshot = DataSnapshot(
            data=MappingProxyType({}),
            source_files=frozenset(),
        )
        assert len(snapshot.data) == 0
        assert len(snapshot.source_files) == 0

    def test_get_method(self) -> None:
        """DataSnapshot.get returns data by key."""
        snapshot = DataSnapshot(
            data=MappingProxyType({"name": "test", "version": "1.0"}),
            source_files=frozenset(),
        )
        assert snapshot.get("name") == "test"
        assert snapshot.get("missing", "default") == "default"

    def test_getitem(self) -> None:
        """DataSnapshot supports dict-style access."""
        snapshot = DataSnapshot(
            data=MappingProxyType({"key": "value"}),
            source_files=frozenset(),
        )
        assert snapshot["key"] == "value"

    def test_contains(self) -> None:
        """DataSnapshot supports 'in' operator."""
        snapshot = DataSnapshot(
            data=MappingProxyType({"exists": True}),
            source_files=frozenset(),
        )
        assert "exists" in snapshot
        assert "missing" not in snapshot


class TestLoadDataDirectory:
    """Tests for load_data_directory function."""

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """load_data_directory handles nonexistent data/ dir."""
        snapshot = load_data_directory(tmp_path)
        assert len(snapshot.data) == 0
        assert len(snapshot.source_files) == 0

    def test_load_json_file(self, tmp_path: Path) -> None:
        """load_data_directory loads JSON files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "config.json").write_text('{"name": "test", "count": 42}')
        
        snapshot = load_data_directory(tmp_path)
        
        assert "config" in snapshot
        assert snapshot["config"]["name"] == "test"
        assert snapshot["config"]["count"] == 42
        assert len(snapshot.source_files) == 1

    def test_load_yaml_file(self, tmp_path: Path) -> None:
        """load_data_directory loads YAML files."""
        pytest.importorskip("yaml")
        
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "settings.yaml").write_text("title: My Site\nenabled: true")
        
        snapshot = load_data_directory(tmp_path)
        
        assert "settings" in snapshot
        assert snapshot["settings"]["title"] == "My Site"
        assert snapshot["settings"]["enabled"] is True

    def test_nested_structure(self, tmp_path: Path) -> None:
        """load_data_directory creates nested structure from subdirs."""
        data_dir = tmp_path / "data"
        (data_dir / "team").mkdir(parents=True)
        (data_dir / "team" / "members.json").write_text('[{"name": "Alice"}]')
        
        snapshot = load_data_directory(tmp_path)
        
        assert "team" in snapshot
        assert "members" in snapshot["team"]
        # Note: lists become tuples when frozen
        assert snapshot["team"]["members"][0]["name"] == "Alice"

    def test_skips_unsupported_extensions(self, tmp_path: Path) -> None:
        """load_data_directory skips unsupported file types."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "readme.txt").write_text("This is readme")
        (data_dir / "config.json").write_text('{"valid": true}')
        
        snapshot = load_data_directory(tmp_path)
        
        assert "readme" not in snapshot
        assert "config" in snapshot


class TestGetData:
    """Tests for get_data function."""

    def test_top_level_key(self) -> None:
        """get_data retrieves top-level key."""
        snapshot = DataSnapshot(
            data=MappingProxyType({"name": "test"}),
            source_files=frozenset(),
        )
        result = get_data(snapshot, "name")
        assert result == "test"

    def test_dot_notation_key(self) -> None:
        """get_data retrieves nested key with dot notation."""
        snapshot = DataSnapshot(
            data=MappingProxyType({
                "site": MappingProxyType({
                    "name": "My Site",
                    "author": MappingProxyType({"name": "John"}),
                })
            }),
            source_files=frozenset(),
        )
        assert get_data(snapshot, "site.name") == "My Site"
        assert get_data(snapshot, "site.author.name") == "John"

    def test_missing_key_returns_default(self) -> None:
        """get_data returns default for missing key."""
        snapshot = DataSnapshot(
            data=MappingProxyType({}),
            source_files=frozenset(),
        )
        result = get_data(snapshot, "missing", default="fallback")
        assert result == "fallback"

    def test_partial_path_returns_default(self) -> None:
        """get_data returns default when path partially exists."""
        snapshot = DataSnapshot(
            data=MappingProxyType({"a": MappingProxyType({"b": "value"})}),
            source_files=frozenset(),
        )
        result = get_data(snapshot, "a.b.c", default="nope")
        assert result == "nope"


class TestDataService:
    """Tests for DataService class."""

    def test_create_from_root(self, tmp_path: Path) -> None:
        """DataService can be created from root path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "config.json").write_text('{"key": "value"}')
        
        service = DataService.from_root(tmp_path)
        assert service.get("config.key") == "value"

    def test_get_method(self, tmp_path: Path) -> None:
        """DataService.get returns data by dot-notation key."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "settings.json").write_text('{"theme": "dark"}')
        
        service = DataService.from_root(tmp_path)
        assert service.get("settings.theme") == "dark"
        assert service.get("missing", "default") == "default"
