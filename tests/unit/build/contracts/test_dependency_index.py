"""Tests for dependency index read-model contracts."""

from __future__ import annotations

from bengal.build.contracts.dependency_index import (
    DependencyIndexEntry,
    DependencyReadIndex,
    build_dependency_read_index,
)
from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.types import ContentHash, Provenance, ProvenanceRecord


def test_dependency_index_entry_normalizes_keys() -> None:
    """Entries dedupe and sort page/output keys for deterministic cache payloads."""
    entry = DependencyIndexEntry(
        dependency_kind="template",
        dependency_key="base.html",
        page_keys=("content/b.md", "content/a.md", "content/a.md"),
        output_keys=("public/b/index.html", "public/a/index.html"),
        invalidation_reason="template_changed",
        producer="provenance",
    )

    assert entry.page_keys == ("content/a.md", "content/b.md")
    assert entry.output_keys == ("public/a/index.html", "public/b/index.html")


def test_dependency_index_entry_round_trip() -> None:
    """Entries serialize without losing invalidation diagnostics."""
    entry = DependencyIndexEntry(
        dependency_kind="data",
        dependency_key="data/team.yaml",
        page_keys=("content/about.md",),
        output_keys=("public/about/index.html",),
        invalidation_reason="data_dependency_changed",
        producer="effect-provenance",
    )

    restored = DependencyIndexEntry.from_cache_dict(entry.to_cache_dict())

    assert restored == entry


def test_dependency_read_index_returns_affected_keys() -> None:
    """Read index exposes page and output lookups without detector side effects."""
    index = DependencyReadIndex(
        [
            DependencyIndexEntry(
                dependency_kind="template",
                dependency_key="base.html",
                page_keys=("content/a.md",),
                output_keys=("public/a/index.html",),
                invalidation_reason="template_changed",
            )
        ]
    )

    assert index.affected_page_keys("template", "base.html") == ("content/a.md",)
    assert index.affected_output_keys("template", "base.html") == ("public/a/index.html",)
    assert index.affected_page_keys("template", "missing.html") == ()


def test_dependency_read_index_round_trip() -> None:
    """Read indexes round-trip through a stable dictionary shape."""
    index = DependencyReadIndex(
        [
            DependencyIndexEntry(
                dependency_kind="generated",
                dependency_key="tags/python",
                page_keys=("content/a.md", "content/b.md"),
                output_keys=("public/tags/python/index.html",),
                invalidation_reason="generated_members_changed",
                producer="page-artifacts",
            )
        ]
    )

    restored = DependencyReadIndex.from_cache_dict(index.to_cache_dict())

    assert restored.affected_page_keys("generated", "tags/python") == (
        "content/a.md",
        "content/b.md",
    )
    assert restored.affected_output_keys("generated", "tags/python") == (
        "public/tags/python/index.html",
    )


def test_dependency_read_index_skips_malformed_entries() -> None:
    """Malformed cache entries do not poison the whole read index."""
    restored = DependencyReadIndex.from_cache_dict(
        {
            "bad": {
                "dependency_kind": "data",
                "dependency_key": "data/bad.yaml",
                "page_keys": None,
            },
            "worse": ["not", "a", "mapping"],
            "good": {
                "dependency_kind": "data",
                "dependency_key": "data/good.yaml",
                "page_keys": ["content/good.md"],
            },
        }
    )

    assert restored.affected_page_keys("data", "data/good.yaml") == ("content/good.md",)


def test_build_dependency_read_index_from_provenance_records() -> None:
    """Existing provenance records can produce dependency-to-page lookups."""
    page_a = ProvenanceRecord(
        page_path=CacheKey("content/a.md"),
        provenance=Provenance()
        .with_input("content", CacheKey("content/a.md"), ContentHash("a"))
        .with_input("template", CacheKey("templates/page.html"), ContentHash("tpl"))
        .with_input("config", CacheKey("site_config"), ContentHash("cfg")),
        output_hash=ContentHash("out-a"),
    )
    page_b = ProvenanceRecord(
        page_path=CacheKey("content/b.md"),
        provenance=Provenance().with_input(
            "template", CacheKey("templates/page.html"), ContentHash("tpl")
        ),
        output_hash=ContentHash("out-b"),
    )

    index = build_dependency_read_index(
        [page_a, page_b],
        output_keys={
            CacheKey("content/a.md"): ("public/a/index.html",),
            CacheKey("content/b.md"): ("public/b/index.html",),
        },
    )

    assert index.affected_page_keys("template", "templates/page.html") == (
        "content/a.md",
        "content/b.md",
    )
    assert index.affected_output_keys("template", "templates/page.html") == (
        "public/a/index.html",
        "public/b/index.html",
    )
    assert index.affected_page_keys("config", "site_config") == ()
