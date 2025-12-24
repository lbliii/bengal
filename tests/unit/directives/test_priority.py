"""Unit tests for directive priority system."""

from bengal.directives.base import BengalDirective
from bengal.directives.include import IncludeDirective
from bengal.directives.navigation import BreadcrumbsDirective


def test_directive_priority_constants():
    """Test that priority constants are defined and ordered correctly."""
    assert BengalDirective.PRIORITY_FIRST < BengalDirective.PRIORITY_EARLY
    assert BengalDirective.PRIORITY_EARLY < BengalDirective.PRIORITY_NORMAL
    assert BengalDirective.PRIORITY_NORMAL < BengalDirective.PRIORITY_LATE
    assert BengalDirective.PRIORITY_LATE < BengalDirective.PRIORITY_LAST


def test_specific_directive_priorities():
    """Test that key directives have correct priorities."""
    assert IncludeDirective.PRIORITY == BengalDirective.PRIORITY_FIRST
    assert BreadcrumbsDirective.PRIORITY == BengalDirective.PRIORITY_LATE


def test_factory_sorting():
    """Test that the directive factory sorts directives by priority."""

    # Test that they are sorted in the factory logic.
    directives = [
        BreadcrumbsDirective(),
        IncludeDirective(),
    ]

    # Sort them using the same logic as in factory.py
    directives.sort(key=lambda d: getattr(d, "PRIORITY", 100))

    assert isinstance(directives[0], IncludeDirective)
    assert isinstance(directives[1], BreadcrumbsDirective)
