"""Factory function for creating the documentation directives Mistune plugin.

This module provides ``create_documentation_directives()``, which assembles
all Bengal directives into a single Mistune plugin. The plugin uses
``FencedDirective`` to parse MyST-style ``:::{name}`` directive blocks.

Available Directive Categories:
    - **Admonitions**: note, tip, warning, danger, error, info, example, success
    - **Layout**: tabs, cards, container, steps, dropdown
    - **Tables**: list-table, data-table
    - **Code**: code-tabs, literalinclude
    - **Media**: youtube, vimeo, video, audio, figure, gallery
    - **Embeds**: gist, codepen, codesandbox, stackblitz, asciinema
    - **Navigation**: breadcrumbs, siblings, prev-next, related
    - **Versioning**: since, deprecated, changed
    - **Utilities**: badge, button, icon, rubric, target, include, glossary

Example:
    Create a Mistune markdown instance with directive support::

        import mistune
        from bengal.directives import create_documentation_directives

        md = mistune.create_markdown(
            plugins=[create_documentation_directives()]
        )
        html = md(":::{note}\\nThis is important.\\n:::")

Architecture:
    This module imports all directive classes from ``bengal.directives.*``
    and wraps them with ``FencedDirective`` for Mistune integration. Only
    colon-fence syntax (``:::``) is enabled to avoid conflicts with code
    blocks that use backticks.

See Also:
    - ``bengal.directives.registry``: Lazy-loading registry for individual access.
    - ``bengal.directives.fenced``: Mistune fence parsing infrastructure.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Import directive classes from local package
from bengal.directives.admonitions import AdmonitionDirective
from bengal.directives.badge import BadgeDirective
from bengal.directives.build import BuildDirective
from bengal.directives.button import ButtonDirective
from bengal.directives.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
)
from bengal.directives.checklist import ChecklistDirective
from bengal.directives.code_tabs import CodeTabsDirective
from bengal.directives.container import ContainerDirective
from bengal.directives.data_table import DataTableDirective
from bengal.directives.dropdown import DropdownDirective
from bengal.directives.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    StackBlitzDirective,
)
from bengal.directives.example_label import ExampleLabelDirective
from bengal.directives.fenced import FencedDirective
from bengal.directives.figure import AudioDirective, FigureDirective
from bengal.directives.gallery import GalleryDirective
from bengal.directives.glossary import GlossaryDirective
from bengal.directives.icon import IconDirective
from bengal.directives.include import IncludeDirective
from bengal.directives.list_table import ListTableDirective
from bengal.directives.literalinclude import LiteralIncludeDirective
from bengal.directives.marimo import MarimoCellDirective
from bengal.directives.navigation import (
    BreadcrumbsDirective,
    PrevNextDirective,
    RelatedDirective,
    SiblingsDirective,
)
from bengal.directives.rubric import RubricDirective
from bengal.directives.steps import StepDirective, StepsDirective
from bengal.directives.tabs import TabItemDirective, TabSetDirective
from bengal.directives.target import TargetDirective
from bengal.directives.terminal import AsciinemaDirective
from bengal.directives.versioning import (
    ChangedDirective,
    DeprecatedDirective,
    SinceDirective,
)
from bengal.directives.video import (
    SelfHostedVideoDirective,
    VimeoDirective,
    YouTubeDirective,
)
from bengal.utils.logger import get_logger


def create_documentation_directives() -> Callable[[Any], None]:
    """Create the documentation directives plugin for Mistune.

    Assembles all Bengal directives into a single plugin function that can
    be passed to ``mistune.create_markdown(plugins=[...])``.

    Returns:
        A plugin function that registers all directives with a Mistune instance.

    Raises:
        BengalRenderingError: If directive registration fails due to plugin errors.

    Directive Categories:
        **Content Structure**:
            - ``admonitions``: note, tip, warning, danger, error, info, example, success
            - ``dropdown``: Collapsible sections with full markdown support
            - ``tabs``: Tabbed content containers (tab-set, tab-item)
            - ``steps``: Visual step-by-step guides
            - ``cards``: Modern card grid layouts
            - ``container``: Generic wrapper div with CSS classes
            - ``checklist``: Styled checklist containers

        **Tables and Data**:
            - ``list-table``: MyST-style tables using nested lists
            - ``data-table``: Interactive tables with Tabulator.js

        **Code and Includes**:
            - ``code-tabs``: Code examples in multiple languages
            - ``literalinclude``: Include code files with syntax highlighting
            - ``include``: Include markdown files directly

        **Media Embeds**:
            - ``youtube``, ``vimeo``, ``video``: Video embeds (privacy-friendly)
            - ``audio``, ``figure``, ``gallery``: Audio, images, and galleries
            - ``gist``, ``codepen``, ``codesandbox``, ``stackblitz``: Developer embeds
            - ``asciinema``: Terminal recording embeds

        **Navigation**:
            - ``breadcrumbs``, ``siblings``, ``prev-next``, ``related``

        **Versioning**:
            - ``since``, ``deprecated``, ``changed``

        **Utilities**:
            - ``badge``, ``button``, ``icon``, ``rubric``, ``target``, ``glossary``

    Example:
        ::

            import mistune
            from bengal.directives import create_documentation_directives

            md = mistune.create_markdown(
                plugins=[create_documentation_directives()]
            )
            html = md(":::{note}\\nImportant information.\\n:::")

    Note:
        The ``marimo`` directive is conditionally enabled only if the
        ``marimo`` package is installed.
    """

    def plugin_documentation_directives(md: Any) -> None:
        """Register all documentation directives with a Mistune instance.

        Args:
            md: Mistune Markdown instance to register directives with.

        Raises:
            BengalRenderingError: If directive registration fails.
        """
        logger = get_logger(__name__)

        try:
            # Build directive list
            directives_list = [
                AdmonitionDirective(),  # Supports note, tip, warning, etc.
                BadgeDirective(),  # MyST badge directive: {badge} Text :class: badge-class
                BuildDirective(),  # Build badge: embeds /bengal/build.svg
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
                # Gallery
                GalleryDirective(),  # Responsive image galleries with lightbox
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
            from bengal.errors import BengalRenderingError

            raise BengalRenderingError(
                f"Failed to register directives plugin: {e}",
                suggestion="Check directive plugin implementation and dependencies",
                original_error=e,
            ) from e

    return plugin_documentation_directives
