"""
Unit tests for bengal.build.provenance.types.

Tests ContentHash, InputRecord, Provenance, and ProvenanceRecord.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.types import (
    ContentHash,
    InputRecord,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)


# =============================================================================
# hash_content Tests
# =============================================================================


class TestHashContent:
    """Tests for hash_content function."""

    def test_string_input(self) -> None:
        """String input is hashed correctly."""
        result = hash_content("hello world")
        assert isinstance(result, str)
        assert len(result) == 16  # Default truncation

    def test_bytes_input(self) -> None:
        """Bytes input is hashed correctly."""
        result = hash_content(b"hello world")
        assert isinstance(result, str)
        assert len(result) == 16

    def test_custom_truncation(self) -> None:
        """Custom truncation length is applied."""
        result = hash_content("test", truncate=8)
        assert len(result) == 8

    def test_deterministic(self) -> None:
        """Same input produces same hash."""
        hash1 = hash_content("test content")
        hash2 = hash_content("test content")
        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        """Different content produces different hash."""
        hash1 = hash_content("content A")
        hash2 = hash_content("content B")
        assert hash1 != hash2


# =============================================================================
# hash_file Tests
# =============================================================================


class TestHashFile:
    """Tests for hash_file function."""

    def test_existing_file(self, tmp_path: Path) -> None:
        """Existing file is hashed correctly."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("file content")

        result = hash_file(file_path)

        assert isinstance(result, str)
        assert len(result) == 16

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file returns special hash."""
        file_path = tmp_path / "nonexistent.txt"

        result = hash_file(file_path)

        assert result == "_missing_"

    def test_deterministic(self, tmp_path: Path) -> None:
        """Same file content produces same hash."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("file content")

        hash1 = hash_file(file_path)
        hash2 = hash_file(file_path)

        assert hash1 == hash2


# =============================================================================
# hash_dict Tests
# =============================================================================


class TestHashDict:
    """Tests for hash_dict function."""

    def test_empty_dict(self) -> None:
        """Empty dict produces valid hash."""
        result = hash_dict({})
        assert isinstance(result, str)
        assert len(result) == 16

    def test_simple_dict(self) -> None:
        """Simple dict is hashed correctly."""
        result = hash_dict({"key": "value"})
        assert isinstance(result, str)

    def test_nested_dict(self) -> None:
        """Nested dict is hashed correctly."""
        result = hash_dict({"outer": {"inner": "value"}})
        assert isinstance(result, str)

    def test_deterministic(self) -> None:
        """Same dict produces same hash."""
        data = {"key1": "value1", "key2": 123}
        hash1 = hash_dict(data)
        hash2 = hash_dict(data)
        assert hash1 == hash2

    def test_key_order_independent(self) -> None:
        """Key order doesn't affect hash (sort_keys=True)."""
        hash1 = hash_dict({"a": 1, "b": 2})
        hash2 = hash_dict({"b": 2, "a": 1})
        assert hash1 == hash2


# =============================================================================
# InputRecord Tests
# =============================================================================


class TestInputRecord:
    """Tests for InputRecord dataclass."""

    def test_creates_with_fields(self) -> None:
        """InputRecord can be created with all fields."""
        record = InputRecord(
            input_type="content",
            path=CacheKey("content/about.md"),
            hash=ContentHash("abc123"),
        )
        assert record.input_type == "content"
        assert record.path == CacheKey("content/about.md")
        assert record.hash == ContentHash("abc123")

    def test_str_representation(self) -> None:
        """__str__ returns expected format."""
        record = InputRecord(
            input_type="template",
            path=CacheKey("templates/base.html"),
            hash=ContentHash("xyz789"),
        )
        assert str(record) == "template:templates/base.html=xyz789"

    def test_is_frozen(self) -> None:
        """InputRecord is immutable (frozen)."""
        record = InputRecord(
            input_type="data",
            path=CacheKey("data/team.yaml"),
            hash=ContentHash("abc123"),
        )
        with pytest.raises(AttributeError):
            record.input_type = "content"  # type: ignore[misc]


# =============================================================================
# Provenance Tests
# =============================================================================


class TestProvenance:
    """Tests for Provenance dataclass."""

    def test_empty_provenance(self) -> None:
        """Empty provenance has default values."""
        prov = Provenance()
        assert prov.inputs == frozenset()
        # combined_hash is empty string when no inputs
        assert prov.combined_hash == ""

    def test_creates_with_inputs(self) -> None:
        """Provenance can be created with inputs."""
        inputs = frozenset(
            [
                InputRecord("content", CacheKey("content/a.md"), ContentHash("abc")),
                InputRecord("template", CacheKey("templates/b.html"), ContentHash("xyz")),
            ]
        )
        prov = Provenance(inputs=inputs)
        assert len(prov.inputs) == 2

    def test_combined_hash_computed_automatically(self) -> None:
        """Combined hash is computed from inputs."""
        inputs = frozenset(
            [
                InputRecord("content", CacheKey("content/a.md"), ContentHash("abc123")),
            ]
        )
        prov = Provenance(inputs=inputs)
        assert prov.combined_hash != ""
        assert len(prov.combined_hash) == 16

    def test_with_input_adds_input(self) -> None:
        """with_input() adds new input."""
        prov = Provenance()
        new_prov = prov.with_input(
            input_type="content",
            path=CacheKey("content/about.md"),
            content_hash=ContentHash("abc123"),
        )
        assert len(new_prov.inputs) == 1
        assert len(prov.inputs) == 0  # Original unchanged

    def test_merge_combines_inputs(self) -> None:
        """merge() combines inputs from both provenances."""
        prov1 = Provenance().with_input("content", CacheKey("a.md"), ContentHash("abc"))
        prov2 = Provenance().with_input("template", CacheKey("b.html"), ContentHash("xyz"))

        merged = prov1.merge(prov2)

        assert len(merged.inputs) == 2

    def test_input_count(self) -> None:
        """input_count returns number of inputs."""
        prov = Provenance().with_input("content", CacheKey("a.md"), ContentHash("abc"))
        prov = prov.with_input("template", CacheKey("b.html"), ContentHash("xyz"))

        assert prov.input_count == 2

    def test_inputs_by_type(self) -> None:
        """inputs_by_type() filters by input type."""
        prov = Provenance()
        prov = prov.with_input("content", CacheKey("a.md"), ContentHash("abc"))
        prov = prov.with_input("content", CacheKey("b.md"), ContentHash("def"))
        prov = prov.with_input("template", CacheKey("base.html"), ContentHash("xyz"))

        content_inputs = prov.inputs_by_type("content")
        template_inputs = prov.inputs_by_type("template")

        assert len(content_inputs) == 2
        assert len(template_inputs) == 1

    def test_summary(self) -> None:
        """summary() returns human-readable string."""
        prov = Provenance()
        prov = prov.with_input("content", CacheKey("a.md"), ContentHash("abc"))
        prov = prov.with_input("template", CacheKey("b.html"), ContentHash("xyz"))

        summary = prov.summary()

        assert "1 content" in summary
        assert "1 template" in summary
        assert prov.combined_hash in summary

    def test_is_frozen(self) -> None:
        """Provenance is immutable (frozen)."""
        prov = Provenance()
        with pytest.raises(AttributeError):
            prov.inputs = frozenset()  # type: ignore[misc]


# =============================================================================
# ProvenanceRecord Tests
# =============================================================================


class TestProvenanceRecord:
    """Tests for ProvenanceRecord dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """ProvenanceRecord can be created with required fields."""
        prov = Provenance()
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=prov,
            output_hash=ContentHash("output123"),
        )
        assert record.page_path == CacheKey("content/about.md")
        assert record.provenance is prov
        assert record.output_hash == ContentHash("output123")

    def test_default_created_at(self) -> None:
        """created_at defaults to current time."""
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=Provenance(),
            output_hash=ContentHash("output123"),
        )
        assert isinstance(record.created_at, datetime)

    def test_to_dict(self) -> None:
        """to_dict() returns serializable dict."""
        prov = Provenance().with_input(
            "content", CacheKey("content/about.md"), ContentHash("abc123")
        )
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=prov,
            output_hash=ContentHash("output123"),
            build_id="build-001",
        )

        data = record.to_dict()

        assert data["page_path"] == "content/about.md"
        assert data["output_hash"] == "output123"
        assert data["build_id"] == "build-001"
        assert isinstance(data["inputs"], list)
        assert len(data["inputs"]) == 1

    def test_from_dict(self) -> None:
        """from_dict() deserializes correctly."""
        data = {
            "page_path": "content/about.md",
            "inputs": [{"type": "content", "path": "content/about.md", "hash": "abc123"}],
            "combined_hash": "combined123",
            "output_hash": "output123",
            "created_at": "2026-01-16T12:00:00",
            "build_id": "build-001",
        }

        record = ProvenanceRecord.from_dict(data)

        assert record.page_path == CacheKey("content/about.md")
        assert record.output_hash == ContentHash("output123")
        assert record.build_id == "build-001"
        assert len(record.provenance.inputs) == 1

    def test_roundtrip_serialization(self) -> None:
        """to_dict() and from_dict() are inverses."""
        prov = Provenance().with_input(
            "content", CacheKey("content/about.md"), ContentHash("abc123")
        )
        original = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=prov,
            output_hash=ContentHash("output123"),
            build_id="build-001",
        )

        data = original.to_dict()
        recovered = ProvenanceRecord.from_dict(data)

        assert recovered.page_path == original.page_path
        assert recovered.output_hash == original.output_hash
        assert recovered.build_id == original.build_id
        assert len(recovered.provenance.inputs) == len(original.provenance.inputs)
