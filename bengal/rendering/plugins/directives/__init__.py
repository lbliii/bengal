"""
Mistune directives package.

Provides all documentation directives (admonitions, tabs, dropdown, code-tabs)
as a single factory function for easy registration with Mistune.

Also provides:
- Directive caching for performance
- Error handling and validation
- KNOWN_DIRECTIVE_NAMES: Single source of truth for all registered directive names

Directive System v2:
- BengalDirective: Base class for typed directives with contract validation
- DirectiveToken: Typed AST token structure
- DirectiveOptions: Typed option parsing with coercion
- DirectiveContract: Nesting validation for parent-child relationships

See: plan/active/rfc-directive-system-v2.md for architecture details.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bengal.rendering.plugins.directives.admonitions import AdmonitionDirective
from bengal.rendering.plugins.directives.badge import BadgeDirective

# Directive System v2 - Foundation Classes
from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.button import ButtonDirective
from bengal.rendering.plugins.directives.cache import (
    DirectiveCache,
    clear_cache,
    configure_cache,
    get_cache,
    get_cache_stats,
)
from bengal.rendering.plugins.directives.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
    GridDirective,
    GridItemCardDirective,
)
from bengal.rendering.plugins.directives.checklist import ChecklistDirective
from bengal.rendering.plugins.directives.code_tabs import CodeTabsDirective
from bengal.rendering.plugins.directives.container import ContainerDirective
from bengal.rendering.plugins.directives.contracts import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    CODE_TABS_CONTRACT,
    STEP_CONTRACT,
    STEPS_CONTRACT,
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
    ContractValidator,
    ContractViolation,
    DirectiveContract,
)
from bengal.rendering.plugins.directives.data_table import DataTableDirective
from bengal.rendering.plugins.directives.dropdown import DropdownDirective
from bengal.rendering.plugins.directives.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    StackBlitzDirective,
)
from bengal.rendering.plugins.directives.errors import DirectiveError, format_directive_error
from bengal.rendering.plugins.directives.example_label import ExampleLabelDirective
from bengal.rendering.plugins.directives.figure import AudioDirective, FigureDirective
from bengal.rendering.plugins.directives.fenced import FencedDirective
from bengal.rendering.plugins.directives.glossary import GlossaryDirective
from bengal.rendering.plugins.directives.icon import IconDirective
from bengal.rendering.plugins.directives.include import IncludeDirective
from bengal.rendering.plugins.directives.list_table import ListTableDirective
from bengal.rendering.plugins.directives.literalinclude import LiteralIncludeDirective
from bengal.rendering.plugins.directives.marimo import MarimoCellDirective
from bengal.rendering.plugins.directives.navigation import (
    BreadcrumbsDirective,
    PrevNextDirective,
    RelatedDirective,
    SiblingsDirective,
)
from bengal.rendering.plugins.directives.options import (
    ContainerOptions,
    DirectiveOptions,
    StyledOptions,
    TitledOptions,
)
from bengal.rendering.plugins.directives.rubric import RubricDirective
from bengal.rendering.plugins.directives.steps import StepDirective, StepsDirective
from bengal.rendering.plugins.directives.tabs import (
    TabItemDirective,
    TabsDirective,
    TabSetDirective,
)
from bengal.rendering.plugins.directives.terminal import AsciinemaDirective
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.rendering.plugins.directives.video import (
    SelfHostedVideoDirective,
    VimeoDirective,
    YouTubeDirective,
)
from bengal.rendering.plugins.directives.utils import (
    attr_str,
    bool_attr,
    build_class_string,
    class_attr,
    data_attrs,
    escape_html,
)
from bengal.rendering.plugins.directives.validator import DirectiveSyntaxValidator
from bengal.utils.logger import get_logger

# =============================================================================
# DIRECTIVE REGISTRY - Single Source of Truth
# =============================================================================
# All directive classes that Bengal registers. Each class has a DIRECTIVE_NAMES
# attribute declaring the directive names it registers.
#
# When adding a new directive:
# 1. Add DIRECTIVE_NAMES class attribute to your directive class
# 2. Add the class to DIRECTIVE_CLASSES below
# 3. Add the class to create_documentation_directives() directives_list
#
# The health check imports KNOWN_DIRECTIVE_NAMES which is computed automatically
# from DIRECTIVE_CLASSES - no manual synchronization needed!
# =============================================================================

DIRECTIVE_CLASSES: list[type] = [
    # Admonitions (note, tip, warning, danger, error, info, example, success, etc.)
    AdmonitionDirective,
    # Badges (badge, bdg)
    BadgeDirective,
    # Buttons (button)
    ButtonDirective,
    # Cards (cards, card, child-cards, grid, grid-item-card)
    CardsDirective,
    CardDirective,
    ChildCardsDirective,
    GridDirective,
    GridItemCardDirective,
    # Tabs (tabs, tab-set, tab-item)
    TabsDirective,
    TabSetDirective,
    TabItemDirective,
    # Dropdowns (dropdown, details)
    DropdownDirective,
    # Code tabs (code-tabs, code_tabs)
    CodeTabsDirective,
    # Tables (list-table, data-table)
    ListTableDirective,
    DataTableDirective,
    # Glossary (glossary)
    GlossaryDirective,
    # Icon (icon, svg-icon)
    IconDirective,
    # Checklist (checklist)
    ChecklistDirective,
    # Container (container, div) - generic wrapper div with class
    ContainerDirective,
    # Steps (steps, step)
    StepsDirective,
    StepDirective,
    # Rubric (rubric)
    RubricDirective,
    # Example label (example-label) - lightweight example section headers
    ExampleLabelDirective,
    # Includes (include, literalinclude)
    IncludeDirective,
    LiteralIncludeDirective,
    # Navigation (breadcrumbs, siblings, prev-next, related)
    BreadcrumbsDirective,
    SiblingsDirective,
    PrevNextDirective,
    RelatedDirective,
    # Marimo (marimo) - optional, works even if marimo package not installed
    MarimoCellDirective,
    # ==========================================================================
    # Media Embed Directives (RFC: plan/active/rfc-media-embed-directives.md)
    # ==========================================================================
    # Video embeds (youtube, vimeo, video)
    YouTubeDirective,
    VimeoDirective,
    SelfHostedVideoDirective,
    # Developer tool embeds (gist, codepen, codesandbox, stackblitz)
    GistDirective,
    CodePenDirective,
    CodeSandboxDirective,
    StackBlitzDirective,
    # Terminal recording embeds (asciinema)
    AsciinemaDirective,
    # Figure and audio embeds (figure, audio)
    FigureDirective,
    AudioDirective,
]


def get_known_directive_names() -> frozenset[str]:
    """
    Derive known directive names from actual directive classes.

    This is the SINGLE SOURCE OF TRUTH. Do not maintain a separate list.
    Each directive class declares its names via the DIRECTIVE_NAMES class attribute.

    Returns:
        Frozenset of all registered directive names.
    """
    names: set[str] = set()
    for cls in DIRECTIVE_CLASSES:
        if hasattr(cls, "DIRECTIVE_NAMES"):
            names.update(cls.DIRECTIVE_NAMES)
        else:
            # Log warning about missing DIRECTIVE_NAMES (shouldn't happen)
            logger = get_logger(__name__)
            logger.warning(
                "directive_missing_names",
                directive=cls.__name__,
                info=f"Directive {cls.__name__} missing DIRECTIVE_NAMES attribute",
            )
    return frozenset(names)


# Cached for performance - computed once at import time
KNOWN_DIRECTIVE_NAMES: frozenset[str] = get_known_directive_names()

# Admonition types subset (for type-specific validation)
ADMONITION_TYPES: frozenset[str] = frozenset(
    {
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
    }
)

# Code-related directives (can use backtick fences)
CODE_BLOCK_DIRECTIVES: frozenset[str] = frozenset(
    {
        "code-tabs",
        "literalinclude",
    }
)

__all__ = [
    # Registry constants and functions (single source of truth)
    "DIRECTIVE_CLASSES",
    "KNOWN_DIRECTIVE_NAMES",
    "get_known_directive_names",
    "ADMONITION_TYPES",
    "CODE_BLOCK_DIRECTIVES",
    # Directive System v2 - Foundation Classes
    "BengalDirective",
    "DirectiveToken",
    "DirectiveOptions",
    "DirectiveContract",
    "ContractValidator",
    "ContractViolation",
    # Preset Options
    "StyledOptions",
    "ContainerOptions",
    "TitledOptions",
    # Preset Contracts
    "STEPS_CONTRACT",
    "STEP_CONTRACT",
    "TAB_SET_CONTRACT",
    "TAB_ITEM_CONTRACT",
    "CARDS_CONTRACT",
    "CARD_CONTRACT",
    "CODE_TABS_CONTRACT",
    # Utilities
    "escape_html",
    "build_class_string",
    "bool_attr",
    "data_attrs",
    "attr_str",
    "class_attr",
    # Legacy Classes and functions
    "DirectiveCache",
    "DirectiveError",
    "DirectiveSyntaxValidator",
    "GlossaryDirective",
    "clear_cache",
    "configure_cache",
    "create_documentation_directives",
    "format_directive_error",
    "get_cache",
    "get_cache_stats",
    # Media Embed Directives
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
]


def create_documentation_directives() -> Callable[[Any], None]:
    """
    Create documentation directives plugin for Mistune.

    Returns a function that can be passed to mistune.create_markdown(plugins=[...]).

    Provides:
    - admonitions: note, tip, warning, danger, error, info, example, success
    - badge: MyST badge directive with custom CSS classes
    - tabs: Tabbed content with full markdown support
    - dropdown: Collapsible sections with markdown
    - code-tabs: Code examples in multiple languages
    - rubric: Pseudo-headings for API documentation (not in TOC)
    - list-table: MyST-style tables using nested lists (avoids pipe character issues)
    - checklist: Styled checklist containers for bullet lists and task lists
    - container: Generic wrapper div with CSS classes (like Sphinx container)
    - include: Include markdown files directly in content
    - literalinclude: Include code files as syntax-highlighted code blocks

    Usage:
        from bengal.rendering.plugins.directives import create_documentation_directives

        md = mistune.create_markdown(
            plugins=[create_documentation_directives()]
        )

    Raises:
        RuntimeError: If directive registration fails
        ImportError: If FencedDirective is not available
    """

    def plugin_documentation_directives(md: Any) -> None:
        """Register all documentation directives with Mistune."""
        logger = get_logger(__name__)

        # Use our patched FencedDirective that supports indentation
        # from mistune.directives import FencedDirective <-- REPLACED

        try:
            # Build directive list
            directives_list = [
                AdmonitionDirective(),  # Supports note, tip, warning, etc.
                BadgeDirective(),  # MyST badge directive: {badge} Text :class: badge-class
                TabsDirective(),  # Legacy tabs (backward compatibility)
                TabSetDirective(),  # Modern MyST tab-set
                TabItemDirective(),  # Modern MyST tab-item
                DropdownDirective(),
                CodeTabsDirective(),
                RubricDirective(),  # Pseudo-headings for API docs
                ExampleLabelDirective(),  # Lightweight example section labels
                ListTableDirective(),  # MyST list-table for tables without pipe issues
                DataTableDirective(),  # Interactive data tables with Tabulator.js
                GlossaryDirective(),  # Key terms from centralized glossary data file
                IconDirective(),  # Inline SVG icons from theme icon library
                CardsDirective(),  # Modern card grid system
                CardDirective(),  # Individual cards
                ChildCardsDirective(),  # Auto-generate cards from children
                GridDirective(),  # Grid layout compatibility
                GridItemCardDirective(),  # Grid item compatibility
                ButtonDirective(),  # Simple button links
                ChecklistDirective(),  # Styled checklist containers
                ContainerDirective(),  # Generic wrapper div with CSS class
                StepsDirective(),  # Visual step-by-step guides
                StepDirective(),  # Individual step (nested in steps)
                IncludeDirective(),  # Include markdown files
                LiteralIncludeDirective(),  # Include code files as code blocks
                # Navigation directives (site tree access)
                BreadcrumbsDirective(),  # Auto-generate breadcrumb navigation
                SiblingsDirective(),  # Show other pages in same section
                PrevNextDirective(),  # Section-aware prev/next navigation
                RelatedDirective(),  # Related content based on tags
                # ==========================================================
                # Media Embed Directives
                # ==========================================================
                # Video embeds
                YouTubeDirective(),  # YouTube with privacy mode (youtube-nocookie.com)
                VimeoDirective(),  # Vimeo with Do Not Track mode
                SelfHostedVideoDirective(),  # Native HTML5 video for local files
                # Developer tool embeds
                GistDirective(),  # GitHub Gists
                CodePenDirective(),  # CodePen pens
                CodeSandboxDirective(),  # CodeSandbox projects
                StackBlitzDirective(),  # StackBlitz projects
                # Terminal recording embeds
                AsciinemaDirective(),  # Terminal recordings from asciinema.org
                # Figure and audio
                FigureDirective(),  # Semantic images with captions
                AudioDirective(),  # Self-hosted audio files
            ]

            # Conditionally add Marimo support (only if marimo is installed)
            try:
                import marimo  # noqa: F401

                directives_list.append(MarimoCellDirective())  # Executable Python cells via Marimo
                logger.info("marimo_directive_enabled", info="Marimo executable cells enabled")
            except ImportError:
                logger.info(
                    "marimo_directive_disabled",
                    info="Marimo not available - {marimo} directive disabled",
                )

            # Create fenced directive with all our custom directives
            # STRICT: Only colon (:) fences allowed - backticks reserved for code blocks
            # This avoids conflicts when directives appear in code examples
            directive = FencedDirective(
                directives_list,
                markers=":",
            )

            # Apply to markdown instance
            return directive(md)
        except Exception as e:
            logger.error("directive_registration_error", error=str(e), error_type=type(e).__name__)
            raise RuntimeError(f"Failed to register directives plugin: {e}") from e

    return plugin_documentation_directives
