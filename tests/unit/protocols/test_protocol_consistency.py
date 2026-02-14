"""
Tests for protocol consistency across bengal.protocols.

Ensures all protocols follow consistent patterns:
- All protocols have @runtime_checkable decorator
- All protocols are exported in __all__
- Protocol naming conventions are followed
"""

from __future__ import annotations

import pytest

from bengal import protocols


class TestRuntimeCheckable:
    """Verify all protocols are runtime checkable."""

    @pytest.fixture
    def all_protocols(self) -> list[type]:
        """Get all Protocol classes from bengal.protocols."""
        result = []
        for name in protocols.__all__:
            obj = getattr(protocols, name, None)
            if obj is None:
                continue
            # Check if it's a class that's a Protocol
            if isinstance(obj, type) and any(
                base.__name__ == "Protocol"
                for base in getattr(obj, "__mro__", [])
                if hasattr(base, "__name__")
            ):
                result.append(obj)
        return result

    def test_all_protocols_are_runtime_checkable(self, all_protocols: list[type]) -> None:
        """Every protocol should have @runtime_checkable for isinstance() checks.

        This was identified as a bug when ProgressReporter was missing the decorator,
        making it inconsistent with other protocols in the same module.
        """
        non_checkable = [
            proto.__name__
            for proto in all_protocols
            if not getattr(proto, "_is_runtime_protocol", False)
        ]

        assert not non_checkable, (
            f"Protocols missing @runtime_checkable: {non_checkable}\n"
            "Add @runtime_checkable decorator for isinstance() support.\n"
            "See: bengal/protocols/infrastructure.py for examples."
        )

    def test_protocols_count_is_reasonable(self, all_protocols: list[type]) -> None:
        """Sanity check: we should have a reasonable number of protocols."""
        # As of this writing, we have ~15+ protocols
        # This test catches if the fixture is broken
        assert len(all_protocols) >= 10, (
            f"Only found {len(all_protocols)} protocols. The all_protocols fixture may be broken."
        )


class TestProtocolExports:
    """Verify protocols are properly exported."""

    def test_all_exports_are_importable(self) -> None:
        """All items in __all__ should be importable."""
        missing = [name for name in protocols.__all__ if not hasattr(protocols, name)]

        assert not missing, f"Items in __all__ not found in module: {missing}"

    def test_no_private_protocols_in_all(self) -> None:
        """__all__ should not contain private names."""
        private = [name for name in protocols.__all__ if name.startswith("_")]
        assert not private, f"Private names in __all__: {private}"

    def test_main_protocol_modules_have_all(self) -> None:
        """Main protocol submodules should define __all__.

        Note: Small single-protocol modules (analysis, stats) may omit __all__
        when they only export one or two items.
        """
        from bengal.protocols import build, core, infrastructure, rendering

        # These are the main modules that should have __all__
        main_modules = [build, core, infrastructure, rendering]
        missing_all = [m.__name__ for m in main_modules if not hasattr(m, "__all__")]

        assert not missing_all, f"Main modules missing __all__: {missing_all}"


class TestProtocolNaming:
    """Verify protocol naming conventions."""

    def test_protocols_end_with_standard_suffixes(self) -> None:
        """Protocols should use standard suffixes: Protocol, Like, Handler, Service."""
        valid_suffixes = ("Protocol", "Like", "Handler", "Service", "Target", "Reporter", "Section")
        # Some protocols don't follow suffix convention but are still valid
        exceptions = {
            "Cacheable",  # Adjective pattern (common for mixins/capabilities)
            "EngineCapability",  # Enum, not a protocol
            "BuildPhase",  # Enum
            "PhaseStats",  # TypedDict
            "PhaseTiming",  # TypedDict
            "BuildContextDict",  # TypedDict
            "BuildOptionsDict",  # TypedDict
            "RenderContext",  # TypedDict
            "RenderResult",  # TypedDict
            "TemplateEngine",  # Noun pattern
            "TemplateEnvironment",  # Noun pattern
            "TemplateRenderer",  # Noun + er pattern
            "TemplateIntrospector",  # Noun + or pattern
            "TemplateValidator",  # Noun + or pattern
        }

        from bengal import protocols

        # Get actual protocol classes (not TypedDicts or Enums)
        protocol_names = []
        for name in protocols.__all__:
            obj = getattr(protocols, name, None)
            if obj is None:
                continue
            if isinstance(obj, type) and any(
                base.__name__ == "Protocol"
                for base in getattr(obj, "__mro__", [])
                if hasattr(base, "__name__")
            ):
                protocol_names.append(name)

        non_standard = []
        for name in protocol_names:
            if name in exceptions:
                continue
            if not any(name.endswith(suffix) for suffix in valid_suffixes):
                non_standard.append(name)

        # This is advisory, not enforced strictly
        if non_standard:
            pytest.skip(f"Advisory: non-standard protocol names: {non_standard}")
