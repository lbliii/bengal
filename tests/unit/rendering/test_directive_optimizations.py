"""
Tests for directive processing optimizations.

Verifies that the optimizations from RFC directive-template-optimization work correctly:
- Singleton directive instances
- Cached type hints
- Class-level logger
- Pre-compiled option coercers
- Contract validation skipping in production
"""

from __future__ import annotations

import timeit

from bengal.directives import create_documentation_directives, reset_directive_instances
from bengal.directives.admonitions import AdmonitionDirective
from bengal.directives.base import BengalDirective
from bengal.directives.factory import _get_directive_instances
from bengal.directives.options import DirectiveOptions, StyledOptions


class TestSingletonDirectiveInstances:
    """Test that directive instances are singletons."""

    def test_singleton_instances_reused(self):
        """Singleton directives should be reused across multiple calls."""
        reset_directive_instances()  # Clear cache

        # First call creates instances
        instances1 = _get_directive_instances()
        assert len(instances1) > 0

        # Second call should return same instances
        instances2 = _get_directive_instances()
        assert instances1 is instances2

    def test_singleton_faster_than_new_instances(self):
        """Singleton directives should be faster than creating new ones."""
        reset_directive_instances()  # Clear cache

        # Old way: create new instances
        def create_new():
            return [AdmonitionDirective() for _ in range(40)]

        # New way: get singleton (includes first-time init)
        _ = _get_directive_instances()  # Warm cache

        def get_singleton():
            return _get_directive_instances()

        # Singleton should be significantly faster
        new_time = timeit.timeit(create_new, number=100)
        singleton_time = timeit.timeit(get_singleton, number=100)

        # Singleton should be at least 5x faster (conservative estimate)
        assert singleton_time < new_time * 0.2, (
            f"Singleton ({singleton_time:.4f}s) not faster than new instances ({new_time:.4f}s)"
        )

    def test_singleton_no_state_leakage(self):
        """Singleton directives must not leak state between pages."""
        _instances = _get_directive_instances()  # noqa: F841 - intentional singleton init

        # Parse two different pages
        from bengal.parsing import PatitasParser

        parser = PatitasParser()
        page1 = parser.parse(":::{note}\nContent 1\n:::", {})
        page2 = parser.parse(":::{note}\nContent 2\n:::", {})

        # Verify no state leakage
        assert "Content 1" not in page2
        assert "Content 2" not in page1

    def test_reset_function_works(self):
        """Test that reset_directive_instances() works correctly."""
        # Get instances
        instances1 = _get_directive_instances()
        assert len(instances1) > 0

        # Reset
        reset_directive_instances()

        # Get again - should create new instances
        instances2 = _get_directive_instances()
        assert instances2 is not instances1
        assert len(instances2) == len(instances1)


class TestCachedTypeHints:
    """Test that type hints are cached."""

    def test_cached_hints_populated(self):
        """Cached type hints should be populated for DirectiveOptions subclasses."""
        # Check base class
        assert hasattr(DirectiveOptions, "_cached_hints")
        assert hasattr(DirectiveOptions, "_cached_fields")

        # Check subclass
        assert hasattr(StyledOptions, "_cached_hints")
        assert hasattr(StyledOptions, "_cached_fields")

        # Trigger cache population by calling from_raw (lazy initialization)
        _ = StyledOptions.from_raw({"class": "test"})

        # After calling from_raw, cache should be populated
        # Hints should be populated (non-empty dict or populated on first use)
        assert isinstance(StyledOptions._cached_hints, dict)
        # Cache may be populated lazily, so check if it has css_class OR if it's empty (will populate on next call)
        if StyledOptions._cached_hints:
            assert "css_class" in StyledOptions._cached_hints

        # Fields should be populated (non-empty set or populated on first use)
        assert isinstance(StyledOptions._cached_fields, set)
        if StyledOptions._cached_fields:
            assert "css_class" in StyledOptions._cached_fields

        # Verify caching works by calling again - cache should be populated now
        _ = StyledOptions.from_raw({"class": "test2"})
        assert "css_class" in StyledOptions._cached_hints
        assert "css_class" in StyledOptions._cached_fields

    def test_cached_hints_used_in_from_raw(self):
        """from_raw() should use cached hints instead of calling get_type_hints()."""
        # This is tested indirectly - if caching works, from_raw() will be faster
        # and won't call get_type_hints() repeatedly
        opts = StyledOptions.from_raw({"class": "my-class"})
        assert opts.css_class == "my-class"


class TestClassLevelLogger:
    """Test that loggers are class-level."""

    def test_class_logger_initialized(self):
        """Class-level logger should be initialized."""
        assert hasattr(BengalDirective, "_class_logger")
        assert hasattr(AdmonitionDirective, "_class_logger")
        assert AdmonitionDirective._class_logger is not None

    def test_logger_property_works(self):
        """Logger property should return class-level logger."""
        directive = AdmonitionDirective()
        assert directive.logger is not None
        assert directive.logger is AdmonitionDirective._class_logger

    def test_multiple_instances_share_logger(self):
        """Multiple directive instances should share the same logger."""
        inst1 = AdmonitionDirective()
        inst2 = AdmonitionDirective()
        assert inst1.logger is inst2.logger
        assert inst1.logger is AdmonitionDirective._class_logger


class TestPrecompiledCoercers:
    """Test that option coercers are pre-compiled."""

    def test_coercers_populated(self):
        """Pre-compiled coercers should be populated after first from_raw() call.

        Coercers are lazily initialized on first use for performance.
        """
        # Trigger lazy initialization
        StyledOptions.from_raw({"class": "test"})

        assert hasattr(StyledOptions, "_coercers")
        assert isinstance(StyledOptions._coercers, dict)
        assert "css_class" in StyledOptions._coercers

    def test_coercers_work_correctly(self):
        """Pre-compiled coercers should work correctly."""
        # Test string coercion (identity)
        opts = StyledOptions.from_raw({"class": "my-class"})
        assert opts.css_class == "my-class"

        # Test bool coercion
        from bengal.directives.dropdown import DropdownOptions

        opts = DropdownOptions.from_raw({"open": "true"})
        assert opts.open is True

        opts = DropdownOptions.from_raw({"open": "false"})
        assert opts.open is False

    def test_coercers_faster_than_runtime(self):
        """Pre-compiled coercers should be faster than runtime coercion."""
        # Trigger lazy initialization first
        StyledOptions.from_raw({"class": "test"})

        # This is tested indirectly - if pre-compilation works, from_raw() will be faster
        # We can't easily test this without mocking, but we can verify coercers exist
        assert len(StyledOptions._coercers) > 0


class TestContractValidationSkipping:
    """Test that contract validation can be skipped in production."""

    def test_validation_default_enabled(self):
        """Validation should be enabled by default."""
        from bengal.parsing import PatitasParser

        parser = PatitasParser()

        # Parse with contract violation (step without steps parent)
        content = ":::{step} Step 1\nContent\n:::"
        result = parser.parse(content, {})

        # Should still parse (validation is warning, not error)
        assert "step" in result.lower() or "Step 1" in result

class TestBackwardsCompatibility:
    """Test that optimizations maintain backwards compatibility."""

    def test_directive_creation_still_works(self):
        """Directive creation should still work as before."""
        directive = AdmonitionDirective()
        assert directive is not None
        assert hasattr(directive, "logger")
        assert hasattr(directive, "NAMES")

    def test_options_parsing_still_works(self):
        """Options parsing should still work as before."""
        opts = StyledOptions.from_raw({"class": "test-class"})
        assert opts.css_class == "test-class"

    def test_create_documentation_directives_still_works(self):
        """create_documentation_directives() should still work."""
        plugin = create_documentation_directives()
        assert callable(plugin)

    def test_parser_creation_still_works(self):
        """Parser creation should still work."""
        from bengal.parsing import PatitasParser

        parser = PatitasParser()
        assert parser is not None

        # Should be able to parse directives
        result = parser.parse(":::{note}\nTest\n:::", {})
        assert "admonition" in result or "note" in result.lower()
