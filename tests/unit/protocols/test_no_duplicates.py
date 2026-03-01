"""
Tests to prevent duplicate protocol definitions.

Ensures protocols aren't redefined outside bengal.protocols/.
This prevents the bug where two different class objects exist for
the same conceptual protocol, causing isinstance() checks to fail.

Background:
    Before consolidation, these protocols were defined in multiple places:
    - PageLike in bengal/protocols/core.py AND bengal/core/page/computed.py
    - Cacheable in bengal/protocols/infrastructure.py AND bengal/cache/cacheable.py
    - OutputCollector in bengal/protocols/infrastructure.py AND bengal/core/output/collector.py
    - ProgressReporter in bengal/protocols/infrastructure.py AND bengal/utils/observability/progress.py

    This caused issues where code using one import path wouldn't recognize
    objects created with another import path.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import ClassVar

import pytest


class TestNoDuplicateProtocols:
    """Prevent protocol definitions outside canonical module."""

    # Protocols that should ONLY be defined in bengal/protocols/
    CANONICAL_PROTOCOLS: ClassVar[set[str]] = {
        # Core protocols
        "PageLike",
        "SectionLike",
        "SiteLike",
        "NavigableSection",
        "QueryableSection",
        # Infrastructure protocols
        "ProgressReporter",
        "Cacheable",
        "OutputCollector",
        "ContentSourceProtocol",
        "OutputTarget",
        # Rendering protocols
        "TemplateRenderer",
        "TemplateIntrospector",
        "TemplateValidator",
        "TemplateEngine",
        "TemplateEnvironment",
        "HighlightService",
        "RoleHandler",
        "DirectiveHandler",
        # Analysis protocols
        "KnowledgeGraphProtocol",
        # Stats protocols
        "BuildStatsProtocol",
        "BuildStateProtocol",
    }

    @pytest.fixture
    def bengal_source_files(self) -> list[Path]:
        """Get all Python files in bengal/, excluding protocols/ and parsing backends.

        Note: Parsing backends (patitas, mistune) have their own internal protocols
        that are specific to their implementations and not duplicates of the
        canonical protocols in bengal.protocols.
        """
        # Navigate from test file to bengal directory
        test_file = Path(__file__)
        bengal_dir = test_file.parents[3] / "bengal"
        protocols_dir = bengal_dir / "protocols"

        # Exclude parsing backends - they have their own internal protocols
        # that serve different purposes than bengal.protocols
        parsing_backends_dir = bengal_dir / "parsing" / "backends"

        if not bengal_dir.exists():
            pytest.skip(f"Bengal directory not found: {bengal_dir}")

        return [
            f
            for f in bengal_dir.rglob("*.py")
            if (
                not str(f).startswith(str(protocols_dir))
                and not str(f).startswith(str(parsing_backends_dir))
                and "__pycache__" not in str(f)
            )
        ]

    def _is_protocol_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition is a Protocol subclass."""
        for base in node.bases:
            # Direct Protocol inheritance
            if isinstance(base, ast.Name) and base.id == "Protocol":
                return True
            # Subscripted Protocol (e.g., Protocol[T])
            if (
                isinstance(base, ast.Subscript)
                and isinstance(base.value, ast.Name)
                and base.value.id == "Protocol"
            ):
                return True
        return False

    def test_no_protocol_redefinitions(self, bengal_source_files: list[Path]) -> None:
        """Canonical protocols should not be redefined elsewhere.

        This test scans all Python files outside bengal/protocols/ and checks
        that none of them define a class that:
        1. Has a name matching one of our canonical protocols
        2. Inherits from Protocol

        Re-exports are allowed (importing and re-exporting from bengal.protocols).
        """
        redefinitions = []

        for filepath in bengal_source_files:
            try:
                source = filepath.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except SyntaxError, UnicodeDecodeError:
                continue

            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ClassDef)
                    and node.name in self.CANONICAL_PROTOCOLS
                    and self._is_protocol_class(node)
                ):
                    rel_path = filepath.relative_to(filepath.parents[3])
                    redefinitions.append(
                        f"  {rel_path}:{node.lineno} - class {node.name}(Protocol)"
                    )

        assert not redefinitions, (
            "Found protocol redefinitions outside bengal/protocols/:\n"
            + "\n".join(redefinitions)
            + "\n\n"
            "These should import from bengal.protocols instead of defining their own.\n"
            "Example fix:\n"
            "  # Instead of:\n"
            "  class PageLike(Protocol): ...\n"
            "  \n"
            "  # Do:\n"
            "  from bengal.protocols import PageLike\n"
        )

    def test_reexport_files_dont_define_protocols(self) -> None:
        """Files that re-export protocols should not define them.

        These files are known to re-export protocols for backwards compatibility.
        They should import from bengal.protocols, not define their own.
        """
        # Navigate from test file to bengal directory
        test_file = Path(__file__)
        bengal_dir = test_file.parents[3] / "bengal"

        reexport_files = [
            bengal_dir / "cache" / "cacheable.py",
            bengal_dir / "core" / "output" / "collector.py",
            bengal_dir / "utils" / "observability" / "progress.py",
        ]

        for filepath in reexport_files:
            if not filepath.exists():
                continue

            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)

            protocol_defs = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef) and self._is_protocol_class(node)
            ]

            assert not protocol_defs, (
                f"{filepath.relative_to(bengal_dir)} defines protocols instead of re-exporting:\n"
                f"  Protocols found: {protocol_defs}\n"
                "These should be imported from bengal.protocols, not defined here."
            )


class TestProtocolImportPatterns:
    """Test that imports follow the canonical pattern."""

    def test_bengal_protocols_is_canonical_source(self) -> None:
        """All canonical protocols should be importable from bengal.protocols."""
        from bengal import protocols

        expected = {
            # Core
            "PageLike",
            "SectionLike",
            "SiteLike",
            "NavigableSection",
            "QueryableSection",
            # Infrastructure
            "ProgressReporter",
            "Cacheable",
            "OutputCollector",
            "ContentSourceProtocol",
            "OutputTarget",
            # Rendering
            "TemplateRenderer",
            "TemplateIntrospector",
            "TemplateValidator",
            "TemplateEngine",
            "TemplateEnvironment",
            "HighlightService",
            "RoleHandler",
            "DirectiveHandler",
            # Analysis
            "KnowledgeGraphProtocol",
            # Stats
            "BuildStatsProtocol",
            "BuildStateProtocol",
        }

        missing = expected - set(dir(protocols))
        assert not missing, f"Protocols missing from bengal.protocols: {missing}"

    def test_protocols_in_all(self) -> None:
        """All protocol names should be in __all__."""
        from bengal import protocols

        protocol_names = {
            "PageLike",
            "SectionLike",
            "SiteLike",
            "NavigableSection",
            "QueryableSection",
            "ProgressReporter",
            "Cacheable",
            "OutputCollector",
            "ContentSourceProtocol",
            "OutputTarget",
            "TemplateRenderer",
            "TemplateIntrospector",
            "TemplateValidator",
            "TemplateEngine",
            "TemplateEnvironment",
            "HighlightService",
            "RoleHandler",
            "DirectiveHandler",
            "KnowledgeGraphProtocol",
            "BuildStatsProtocol",
            "BuildStateProtocol",
        }

        missing_from_all = protocol_names - set(protocols.__all__)
        assert not missing_from_all, f"Protocols not exported in __all__: {missing_from_all}"
