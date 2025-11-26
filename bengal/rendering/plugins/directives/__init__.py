"""
Mistune directives package.

Provides all documentation directives (admonitions, tabs, dropdown, code-tabs)
as a single factory function for easy registration with Mistune.

Also provides:
- Directive caching for performance
- Error handling and validation
"""

from __future__ import annotations

from bengal.rendering.plugins.directives.admonitions import AdmonitionDirective
from bengal.rendering.plugins.directives.badge import BadgeDirective
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
    GridDirective,
    GridItemCardDirective,
)
from bengal.rendering.plugins.directives.checklist import ChecklistDirective
from bengal.rendering.plugins.directives.code_tabs import CodeTabsDirective
from bengal.rendering.plugins.directives.data_table import DataTableDirective
from bengal.rendering.plugins.directives.dropdown import DropdownDirective
from bengal.rendering.plugins.directives.errors import DirectiveError, format_directive_error
from bengal.rendering.plugins.directives.fenced import FencedDirective
from bengal.rendering.plugins.directives.list_table import ListTableDirective
from bengal.rendering.plugins.directives.marimo import MarimoCellDirective
from bengal.rendering.plugins.directives.rubric import RubricDirective
from bengal.rendering.plugins.directives.steps import StepsDirective
from bengal.rendering.plugins.directives.tabs import (
    TabItemDirective,
    TabsDirective,
    TabSetDirective,
)
from bengal.rendering.plugins.directives.validator import DirectiveSyntaxValidator
from bengal.utils.logger import get_logger

__all__ = [
    "DirectiveCache",
    "DirectiveError",
    "DirectiveSyntaxValidator",
    "clear_cache",
    "configure_cache",
    "create_documentation_directives",
    "format_directive_error",
    "get_cache",
    "get_cache_stats",
]


def create_documentation_directives():
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

    Usage:
        from bengal.rendering.plugins.directives import create_documentation_directives

        md = mistune.create_markdown(
            plugins=[create_documentation_directives()]
        )

    Raises:
        RuntimeError: If directive registration fails
        ImportError: If FencedDirective is not available
    """

    def plugin_documentation_directives(md):
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
                ListTableDirective(),  # MyST list-table for tables without pipe issues
                DataTableDirective(),  # Interactive data tables with Tabulator.js
                CardsDirective(),  # Modern card grid system
                CardDirective(),  # Individual cards
                GridDirective(),  # Sphinx-Design compatibility
                GridItemCardDirective(),  # Sphinx-Design compatibility
                ButtonDirective(),  # Simple button links
                ChecklistDirective(),  # Styled checklist containers
                StepsDirective(),  # Visual step-by-step guides
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
            # Support both backtick (`) and colon (:) fences for MyST Markdown compatibility
            directive = FencedDirective(
                directives_list,
                markers="`:",
            )

            # Apply to markdown instance
            return directive(md)
        except Exception as e:
            logger.error("directive_registration_error", error=str(e), error_type=type(e).__name__)
            raise RuntimeError(f"Failed to register directives plugin: {e}") from e

    return plugin_documentation_directives
