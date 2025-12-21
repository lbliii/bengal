"""
Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.
"""

from __future__ import annotations

import re
from re import Match
from typing import Any

from bengal.utils.logger import get_logger

__all__ = ["VariableSubstitutionPlugin"]

logger = get_logger(__name__)


class VariableSubstitutionPlugin:
    """
    Mistune plugin for safe variable substitution in markdown content.

    ARCHITECTURE: Separation of Concerns
    =====================================

    This plugin handles ONLY variable substitution ({{ vars }}) in markdown.
    It operates at the AST level after Mistune parses the markdown structure.

    WHAT THIS HANDLES:
    ------------------
    ✅ {{ page.metadata.xxx }} - Access page frontmatter
    ✅ {{ site.config.xxx }} - Access site configuration
    ✅ {{ page.title }}, {{ page.date }}, etc. - Page properties

    WHAT THIS DOESN'T HANDLE:
    --------------------------
    ❌ {% if condition %} - Conditional blocks
    ❌ {% for item %} - Loop constructs
    ❌ Complex Jinja2 logic

    WHY: Conditionals and loops belong in TEMPLATES, not markdown.

    Example - Using in Markdown:
        Welcome to {{ page.metadata.product_name }} version {{ page.metadata.version }}.

        Connect to {{ page.metadata.api_url }}/users

    Example - Escaping Syntax:
        Use {{/* page.title */}} to display the page title.

        This renders as: Use {{ page.title }} to display the page title.

    Example - Using Conditionals in Templates:
        <!-- templates/page.html -->
        <article>
          {% if page.metadata.beta %}
          <div class="beta-notice">Beta Feature</div>
          {% endif %}

          {{ content }}  <!-- Markdown with {{ vars }} renders here -->
        </article>

    KEY FEATURE: Code blocks stay literal naturally!
    ------------------------------------------------
    Since this plugin only processes text tokens (not code tokens),
    code blocks and inline code automatically preserve their content:

        Use `{{ page.title }}` to show the title.  ← Stays literal in output

        ```python
        # This {{ var }} stays literal too!
        print("{{ page.title }}")
        ```

    This is the RIGHT architectural approach:
    - Single-pass parsing (fast!)
    - Natural code block handling (no escaping needed!)
    - Clear separation: content (markdown) vs logic (templates)
    """

    VARIABLE_PATTERN = re.compile(r"\{\{\s*([^}]+)\s*\}\}")
    # Capture everything between {{/* and */}} without stripping whitespace
    ESCAPE_PATTERN = re.compile(r"\{\{/\*(.+?)\*/\}\}")

    def __init__(self, context: dict[str, Any]):
        """
        Initialize with rendering context.

        Args:
            context: Dict with variables (page, site, config, etc.)
        """
        self.context = context
        self.errors: list[str] = []  # Track substitution errors
        self.escaped_placeholders: dict[str, str] = {}  # Track escaped template syntax

    def update_context(self, context: dict[str, Any]) -> None:
        """
        Update the rendering context (for parser reuse).

        Args:
            context: New context dict with variables (page, site, config, etc.)
        """
        self.context = context
        self.errors = []  # Reset errors for new page
        self.escaped_placeholders = {}  # Reset placeholders

    def __call__(self, md: Any) -> None:
        """Register the plugin with Mistune."""
        if md.renderer and md.renderer.NAME == "html":
            # Store original text renderer
            original_text = md.renderer.text

            # Create wrapped renderer that substitutes variables
            def text_with_substitution(text: str) -> str:
                """Render text with variable substitution."""
                substituted = self.substitute_variables(text)
                result: str = original_text(substituted)
                return result

            # Replace text renderer
            md.renderer.text = text_with_substitution

    def preprocess(self, text: str) -> str:
        """
        Handle escaped syntax {{/* ... */}} before parsing.
        """

        # Step 1: Handle escaped syntax {{/* ... */}} → {{ ... }}
        def save_escaped(match: Match[str]) -> str:
            # Preserve the original content without stripping whitespace
            expr = match.group(1)
            placeholder = f"BENGALESCAPED{len(self.escaped_placeholders)}ENDESC"
            # Store the literal {{ }} for later restoration, preserving whitespace
            self.escaped_placeholders[placeholder] = f"{{{{{expr}}}}}"
            return placeholder

        return self.ESCAPE_PATTERN.sub(save_escaped, text)

    def substitute_variables(self, text: str) -> str:
        """
        Substitute {{ variable }} expressions in text nodes.
        """

        # Step 2: Normal variable substitution
        def replace_var(match: Match[str]) -> str:
            expr = match.group(1).strip()

            # If expression contains filter syntax (|), control flow ({%), or other
            # Jinja2 syntax, keep as literal {{ }} for documentation
            # This prevents docs showing "{{ text | filter }}" from being processed by Jinja2
            if (
                "|" in expr
                or "{%" in expr
                or expr.startswith("#")
                or " if " in expr
                or " for " in expr
            ):
                # Keep as placeholder - will be restored after Mistune
                placeholder = f"BENGALESCAPED{len(self.escaped_placeholders)}ENDESC"
                self.escaped_placeholders[placeholder] = f"{{{{ {expr} }}}}"
                return placeholder

            try:
                # Evaluate expression in context
                result = self._eval_expression(expr)
                if result is None:
                    # Variable not found - treat as documentation example
                    placeholder = f"BENGALESCAPED{len(self.escaped_placeholders)}ENDESC"
                    self.escaped_placeholders[placeholder] = f"{{{{ {expr} }}}}"
                    return placeholder
                return str(result)
            except Exception as e:
                # On error, keep as placeholder for documentation display
                logger.debug(
                    "variable_substitution_failed",
                    expression=expr,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="keeping_as_placeholder",
                )
                placeholder = f"BENGALESCAPED{len(self.escaped_placeholders)}ENDESC"
                self.escaped_placeholders[placeholder] = f"{{{{ {expr} }}}}"
                return placeholder

        return self.VARIABLE_PATTERN.sub(replace_var, text)

    def _substitute_variables(self, text: str) -> str:
        """
        Combines preprocess and substitution.
        """
        text = self.preprocess(text)
        return self.substitute_variables(text)

    def restore_placeholders(self, html: str) -> str:
        """
        Restore placeholders to HTML-escaped template syntax.

        This uses HTML entities to prevent Jinja2 from processing the restored
        template syntax. The browser will render &#123;&#123; as {{ in the final output.

        This is the correct long-term solution because:
        - Jinja2 won't see {{ so it won't try to template it
        - The browser renders entities as literal {{ for users to see
        - No timing issues or re-processing concerns
        - Works for documentation examples, code snippets, etc.

        Args:
            html: HTML output from Mistune

        Returns:
            HTML with placeholders restored as HTML entities
        """
        for placeholder, literal in self.escaped_placeholders.items():
            # Convert {{ and }} to HTML entities so Jinja2 doesn't process them
            html_escaped = literal.replace("{", "&#123;").replace("}", "&#125;")
            html = html.replace(placeholder, html_escaped)
        return html

    def _eval_expression(self, expr: str) -> Any:
        """
        Safely evaluate a simple expression like 'page.metadata.title'.

        Supports dot notation for accessing nested attributes/dict keys.

        SECURITY: Blocks access to private/dunder attributes to prevent:
        - {{ page.__class__.__bases__ }}
        - {{ config.__init__.__globals__ }}
        - {{ page._private_field }}

        Args:
            expr: Expression to evaluate (e.g., 'page.metadata.title')

        Returns:
            Evaluated result

        Raises:
            ValueError: If expression tries to access private/dunder attributes
            ValueError: If key not found or cannot access attribute
        """
        # Support simple dot notation: page.metadata.title
        parts = expr.split(".")

        # SECURITY: Block access to private/dunder attributes
        from bengal.errors import BengalRenderingError

        for part in parts:
            if part.startswith("_"):
                raise BengalRenderingError(
                    f"Access to private/protected attributes denied: '{part}' in '{expr}'",
                    suggestion="Use public attributes only in template expressions",
                )

        result: Any = self.context

        for part in parts:
            # SECURITY: Double-check dunder blocking on actual attribute access
            if part.startswith("_"):
                raise BengalRenderingError(
                    f"Access to private/protected attributes denied: '{part}'",
                    suggestion="Use public attributes only in template expressions",
                )

            if hasattr(result, part):
                result = getattr(result, part)
            elif isinstance(result, dict):
                result = result.get(part)
                if result is None:
                    raise BengalRenderingError(
                        f"Key '{part}' not found in expression '{expr}'",
                        suggestion=f"Check that '{part}' exists in the context dictionary",
                    )
            else:
                raise BengalRenderingError(
                    f"Cannot access '{part}' in expression '{expr}'",
                    suggestion=f"'{part}' is not a valid attribute or key for this object",
                )

        return result
