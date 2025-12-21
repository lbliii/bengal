"""
Tests for directive registry consistency.

Verifies that DIRECTIVE_NAMES class attributes match actual registrations
and that the single source of truth (DIRECTIVE_CLASSES) is complete.

Related:
    - RFC: plan/active/rfc-directive-registry-single-source-of-truth.md
    - Implementation: bengal/rendering/plugins/directives/__init__.py
"""

from __future__ import annotations

import pytest


class TestDirectiveNamesConsistency:
    """Verify DIRECTIVE_NAMES matches actual registrations."""

    def test_all_directive_classes_have_directive_names(self):
        """Every class in DIRECTIVE_CLASSES has DIRECTIVE_NAMES attribute."""
        from bengal.directives import DIRECTIVE_CLASSES

        missing = []
        for cls in DIRECTIVE_CLASSES:
            if not hasattr(cls, "DIRECTIVE_NAMES"):
                missing.append(cls.__name__)

        assert not missing, f"Classes missing DIRECTIVE_NAMES: {missing}"

    def test_directive_names_not_empty(self):
        """Every DIRECTIVE_NAMES attribute is non-empty."""
        from bengal.directives import DIRECTIVE_CLASSES

        empty = []
        for cls in DIRECTIVE_CLASSES:
            if hasattr(cls, "DIRECTIVE_NAMES") and not cls.DIRECTIVE_NAMES:
                empty.append(cls.__name__)

        assert not empty, f"Classes with empty DIRECTIVE_NAMES: {empty}"

    def test_cached_known_names_matches_function(self):
        """Cached KNOWN_DIRECTIVE_NAMES matches get_known_directive_names()."""
        from bengal.directives import (
            KNOWN_DIRECTIVE_NAMES,
            get_known_directive_names,
        )

        computed = get_known_directive_names()
        assert computed == KNOWN_DIRECTIVE_NAMES, (
            f"Cached KNOWN_DIRECTIVE_NAMES differs from computed:\n"
            f"  Cached: {sorted(KNOWN_DIRECTIVE_NAMES)}\n"
            f"  Computed: {sorted(computed)}"
        )

    def test_known_directive_names_is_frozenset(self):
        """KNOWN_DIRECTIVE_NAMES is a frozenset for immutability."""
        from bengal.directives import KNOWN_DIRECTIVE_NAMES

        assert isinstance(KNOWN_DIRECTIVE_NAMES, frozenset)

    def test_no_unexpected_duplicates(self):
        """Check for unintentional duplicate directive names across classes."""
        from bengal.directives import DIRECTIVE_CLASSES

        # Collect all names with their source classes
        name_to_classes: dict[str, list[str]] = {}
        for cls in DIRECTIVE_CLASSES:
            if hasattr(cls, "DIRECTIVE_NAMES"):
                for name in cls.DIRECTIVE_NAMES:
                    if name not in name_to_classes:
                        name_to_classes[name] = []
                    name_to_classes[name].append(cls.__name__)

        # Known intentional aliases (same name registered by multiple classes)
        # Currently none - all aliases are within a single class
        known_shared_names: set[str] = set()

        # Find unexpected duplicates
        unexpected_dups = {
            name: classes
            for name, classes in name_to_classes.items()
            if len(classes) > 1 and name not in known_shared_names
        }

        assert not unexpected_dups, (
            f"Unexpected directive name duplicates across classes:\n  {unexpected_dups}"
        )

    def test_directive_names_lowercase_hyphenated(self):
        """Directive names follow naming convention (lowercase, hyphenated)."""
        from bengal.directives import KNOWN_DIRECTIVE_NAMES

        # Allowed exceptions: code_tabs is an underscore alias for code-tabs
        allowed_exceptions = {"code_tabs"}

        invalid = []
        for name in KNOWN_DIRECTIVE_NAMES:
            if name in allowed_exceptions:
                continue

            # Check: lowercase, no underscores (use hyphens), no spaces
            if not name.islower():
                invalid.append(f"{name} (not lowercase)")
            elif "_" in name:
                invalid.append(f"{name} (has underscore, use hyphen)")
            elif " " in name:
                invalid.append(f"{name} (has space)")

        assert not invalid, f"Directive names violating naming convention: {invalid}"


class TestDirectiveRegistration:
    """Verify DIRECTIVE_NAMES matches what __call__ actually registers."""

    def test_directive_names_match_registration(self):
        """DIRECTIVE_NAMES matches what __call__ actually registers."""

        class MockDirective:
            """Mock directive that captures registered names."""

            def __init__(self):
                self.registered: set[str] = set()

            def register(self, name: str, fn) -> None:
                self.registered.add(name)

        class MockMd:
            """Mock markdown instance."""

            renderer = None

        from bengal.directives import DIRECTIVE_CLASSES

        mismatches = []
        for cls in DIRECTIVE_CLASSES:
            if not hasattr(cls, "DIRECTIVE_NAMES"):
                continue

            mock = MockDirective()
            try:
                instance = cls()
                instance(mock, MockMd())
            except Exception:
                # Some directives may need real md instance - skip
                continue

            declared = set(cls.DIRECTIVE_NAMES)
            registered = mock.registered

            if declared != registered:
                mismatches.append(f"{cls.__name__}: declared {declared} != registered {registered}")

        assert not mismatches, "DIRECTIVE_NAMES mismatches:\n  " + "\n  ".join(mismatches)


class TestDirectiveClassesCompleteness:
    """Verify DIRECTIVE_CLASSES includes all directives used in create_documentation_directives."""

    def test_directive_classes_matches_directives_list(self):
        """DIRECTIVE_CLASSES matches directives_list in create_documentation_directives()."""
        from bengal.directives import register_all
        from bengal.directives.registry import get_directive_classes

        # Register all directives first (lazy loading)
        register_all()

        # Get the class names from the registry
        registry_classes = {cls.__name__ for cls in get_directive_classes()}

        # Expected classes based on create_documentation_directives()
        # Note: This list should match the directives_list in create_documentation_directives
        expected_classes = {
            "AdmonitionDirective",
            "BadgeDirective",
            "BuildDirective",
            "ButtonDirective",
            "CardsDirective",
            "CardDirective",
            "ChildCardsDirective",
            "TabSetDirective",
            "TabItemDirective",
            "DropdownDirective",
            "CodeTabsDirective",
            "ListTableDirective",
            "DataTableDirective",
            "GlossaryDirective",
            "ChecklistDirective",
            "StepsDirective",
            "StepDirective",
            "RubricDirective",
            "ExampleLabelDirective",
            "IncludeDirective",
            "LiteralIncludeDirective",
            "BreadcrumbsDirective",
            "SiblingsDirective",
            "PrevNextDirective",
            "RelatedDirective",
            "MarimoCellDirective",
            "IconDirective",
            "ContainerDirective",
            # Target Directive (RFC: plan/active/rfc-explicit-anchor-targets.md)
            "TargetDirective",
            # Media Embed Directives (RFC: plan/active/rfc-media-embed-directives.md)
            "YouTubeDirective",
            "VimeoDirective",
            "SelfHostedVideoDirective",
            "GistDirective",
            "CodePenDirective",
            "CodeSandboxDirective",
            "StackBlitzDirective",
            "AsciinemaDirective",
            "FigureDirective",
            "AudioDirective",
            # Versioning Directives (RFC: plan/drafted/rfc-versioned-documentation.md)
            "SinceDirective",
            "DeprecatedDirective",
            "ChangedDirective",
        }

        missing = expected_classes - registry_classes
        extra = registry_classes - expected_classes

        assert not missing, f"Classes missing from DIRECTIVE_CLASSES: {missing}"
        assert not extra, f"Extra classes in DIRECTIVE_CLASSES: {extra}"


class TestKnownDirectiveNamesContent:
    """Verify specific expected directives are in KNOWN_DIRECTIVE_NAMES."""

    @pytest.mark.parametrize(
        "directive_name",
        [
            # Admonitions
            "note",
            "tip",
            "warning",
            "danger",
            "error",
            "info",
            "example",
            "success",
            "caution",
            "seealso",
            # Badges
            "badge",
            "bdg",
            # Buttons
            "button",
            # Cards
            "cards",
            "card",
            "child-cards",
            "grid",
            "grid-item-card",
            # Tabs (tab-set has "tabs" alias, tab-item has "tab" alias)
            "tabs",
            "tab-set",
            "tab-item",
            "tab",
            # Code tabs
            "code-tabs",
            # Dropdowns
            "dropdown",
            "details",
            # Tables
            "list-table",
            "data-table",
            # Glossary
            "glossary",
            # Checklist
            "checklist",
            # Steps
            "steps",
            "step",
            # Rubric
            "rubric",
            # Target (explicit anchor targets)
            "target",
            "anchor",
            # Includes
            "include",
            "literalinclude",
            # Navigation
            "breadcrumbs",
            "siblings",
            "prev-next",
            "related",
            # Marimo
            "marimo",
            # Icons
            "icon",
            "svg-icon",
        ],
    )
    def test_expected_directive_present(self, directive_name: str):
        """Each expected directive is present in KNOWN_DIRECTIVE_NAMES."""
        from bengal.directives import KNOWN_DIRECTIVE_NAMES

        assert directive_name in KNOWN_DIRECTIVE_NAMES, (
            f"Expected directive '{directive_name}' not in KNOWN_DIRECTIVE_NAMES"
        )

    def test_known_directive_names_count(self):
        """KNOWN_DIRECTIVE_NAMES has expected count."""
        from bengal.directives import KNOWN_DIRECTIVE_NAMES

        # 10 admonitions + 2 badges + 1 button + 5 cards + 4 tabs (tab-set, tabs, tab-item, tab) + 2 code-tabs
        # + 2 dropdowns + 2 tables + 1 glossary + 1 checklist + 2 steps + 1 rubric
        # + 1 example-label + 2 target/anchor + 2 includes + 4 navigation + 1 marimo + 2 icons + 2 containers
        # + 1 build badge (build)
        # + 3 video (youtube, vimeo, video) + 4 dev tools (gist, codepen, codesandbox, stackblitz)
        # + 1 asciinema + 1 figure + 1 audio = 58 base
        # + 6 versioning (since, deprecated, changed, versionadded, versionchanged, versionremoved) = 64 total
        expected_count = 64

        assert len(KNOWN_DIRECTIVE_NAMES) == expected_count, (
            f"KNOWN_DIRECTIVE_NAMES has {len(KNOWN_DIRECTIVE_NAMES)} items, "
            f"expected {expected_count}\n"
            f"Names: {sorted(KNOWN_DIRECTIVE_NAMES)}"
        )
