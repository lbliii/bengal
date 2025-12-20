"""
Factory function for creating documentation directives plugin.

Provides `create_documentation_directives()` which creates a Mistune plugin
with all Bengal documentation directives registered.

Usage:
    from bengal.directives import create_documentation_directives

    md = mistune.create_markdown(
        plugins=[create_documentation_directives()]
    )

Architecture:
    This module imports directive classes from bengal.directives.* and wraps
    them with FencedDirective (from bengal.rendering.plugins.directives.fenced)
    to create a Mistune-compatible plugin.

    The FencedDirective is kept in bengal.rendering because it's Mistune-specific
    rendering infrastructure, while directive implementations are in bengal.directives.

Related:
    - bengal/directives/registry.py: Lazy-loading directive registry
    - bengal/rendering/plugins/directives/fenced.py: Mistune fence parsing
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Import directive classes directly from implementation location
# (Not via bengal.directives.* to avoid circular import with bengal.rendering.plugins)
from bengal.rendering.plugins.directives.admonitions import AdmonitionDirective
from bengal.rendering.plugins.directives.badge import BadgeDirective
from bengal.rendering.plugins.directives.build import BuildDirective
from bengal.rendering.plugins.directives.button import ButtonDirective
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
from bengal.rendering.plugins.directives.data_table import DataTableDirective
from bengal.rendering.plugins.directives.dropdown import DropdownDirective
from bengal.rendering.plugins.directives.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    StackBlitzDirective,
)
from bengal.rendering.plugins.directives.example_label import ExampleLabelDirective
from bengal.rendering.plugins.directives.fenced import FencedDirective
from bengal.rendering.plugins.directives.figure import AudioDirective, FigureDirective
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
from bengal.rendering.plugins.directives.rubric import RubricDirective
from bengal.rendering.plugins.directives.steps import StepDirective, StepsDirective
from bengal.rendering.plugins.directives.tabs import TabItemDirective, TabSetDirective
from bengal.rendering.plugins.directives.target import TargetDirective
from bengal.rendering.plugins.directives.terminal import AsciinemaDirective
from bengal.rendering.plugins.directives.versioning import (
    ChangedDirective,
    DeprecatedDirective,
    SinceDirective,
)
from bengal.rendering.plugins.directives.video import (
    SelfHostedVideoDirective,
    VimeoDirective,
    YouTubeDirective,
)
from bengal.utils.logger import get_logger


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
        from bengal.directives import create_documentation_directives

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

        try:
            # Build directive list
            directives_list = [
                AdmonitionDirective(),  # Supports note, tip, warning, etc.
                BadgeDirective(),  # MyST badge directive: {badge} Text :class: badge-class
                BuildDirective(),  # Build badge: embeds /bengal/build.svg (optional link to build.json)
                TabSetDirective(),  # MyST tab-set
                TabItemDirective(),  # MyST tab-item
                DropdownDirective(),
                CodeTabsDirective(),
                RubricDirective(),  # Pseudo-headings for API docs
                TargetDirective(),  # Explicit anchor targets for cross-references
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
                # Version-aware directives
                SinceDirective(),  # Mark features added in a version
                DeprecatedDirective(),  # Mark deprecated features
                ChangedDirective(),  # Mark behavior changes
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
