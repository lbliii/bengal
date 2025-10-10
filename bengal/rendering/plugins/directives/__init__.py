"""
Mistune directives package.

Provides all documentation directives (admonitions, tabs, dropdown, code-tabs)
as a single factory function for easy registration with Mistune.

Also provides:
- Directive caching for performance
- Error handling and validation
"""

from bengal.utils.logger import get_logger
from bengal.rendering.plugins.directives.admonitions import AdmonitionDirective
from bengal.rendering.plugins.directives.tabs import TabsDirective
from bengal.rendering.plugins.directives.dropdown import DropdownDirective
from bengal.rendering.plugins.directives.code_tabs import CodeTabsDirective
from bengal.rendering.plugins.directives.rubric import RubricDirective
from bengal.rendering.plugins.directives.cache import (
    DirectiveCache,
    get_cache,
    configure_cache,
    clear_cache,
    get_cache_stats,
)
from bengal.rendering.plugins.directives.errors import DirectiveError, format_directive_error
from bengal.rendering.plugins.directives.validator import DirectiveSyntaxValidator

__all__ = [
    'create_documentation_directives',
    'DirectiveCache',
    'get_cache',
    'configure_cache',
    'clear_cache',
    'get_cache_stats',
    'DirectiveError',
    'format_directive_error',
    'DirectiveSyntaxValidator',
]


def create_documentation_directives():
    """
    Create documentation directives plugin for Mistune.
    
    Returns a function that can be passed to mistune.create_markdown(plugins=[...]).
    
    Provides:
    - admonitions: note, tip, warning, danger, error, info, example, success
    - tabs: Tabbed content with full markdown support
    - dropdown: Collapsible sections with markdown
    - code-tabs: Code examples in multiple languages
    - rubric: Pseudo-headings for API documentation (not in TOC)
    
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
        try:
            from mistune.directives import FencedDirective
        except ImportError as e:
            logger.error("fenced_directive_unavailable",
                        error=str(e),
                        error_type=type(e).__name__)
            raise ImportError(
                "FencedDirective not found. Ensure mistune>=3.0.0 is installed."
            ) from e
        
        try:
            # Create fenced directive with all our custom directives
            directive = FencedDirective([
                AdmonitionDirective(),  # Supports note, tip, warning, etc.
                TabsDirective(),
                DropdownDirective(),
                CodeTabsDirective(),
                RubricDirective(),  # Pseudo-headings for API docs
            ])
            
            # Apply to markdown instance
            return directive(md)
        except Exception as e:
            logger.error("directive_registration_error",
                        error=str(e),
                        error_type=type(e).__name__)
            raise RuntimeError(f"Failed to register directives plugin: {e}") from e
    
    return plugin_documentation_directives

