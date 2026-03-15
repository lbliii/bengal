"""
Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.
"""

from __future__ import annotations

import re
from re import Match
from typing import Any

from bengal.utils.observability.logger import get_logger

__all__ = ["VariableSubstitutionPlugin"]

logger = get_logger(__name__)


class VariableSubstitutionPlugin:
    """
    Structure-aware variable substitution for markdown content.

    ARCHITECTURE: Separation of Concerns
    =====================================

    This plugin handles ONLY variable substitution ({{ vars }}) in markdown.
    It substitutes on inline markdown fragments before inline parsing so links
    still parse correctly, while code spans and fenced code stay literal.

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
    Since this plugin skips code spans and leaves fenced code to block parsing,
    code blocks and inline code preserve their content:

        Use `{{ page.title }}` to show the title.  ← Stays literal in output

            ```python
            # This {{ var }} stays literal too!
            print("{{ page.title }}")
            ```

    This is the pragmatic architectural approach with current Patitas hooks:
    - Structural awareness for inline markdown
    - Natural code fence handling
    - Clear separation: content (markdown) vs logic (templates)

    """

    VARIABLE_PATTERN = re.compile(r"\{\{\s*([^}]+)\s*\}\}")
    # Capture everything between {{/* and */}} without stripping whitespace
    ESCAPE_PATTERN = re.compile(r"\{\{/\*(.+?)\*/\}\}")
    LITERAL_MARKER_START = "BGL["
    LITERAL_MARKER_END = "]LGB"
    LITERAL_MARKER_PATTERN = re.compile(
        rf"{re.escape(LITERAL_MARKER_START)}(.*?){re.escape(LITERAL_MARKER_END)}"
    )

    def __init__(self, context: dict[str, Any]):
        """
        Initialize with rendering context.

        Args:
            context: Dict with variables (page, site, config, etc.)
        """
        self.context = context
        self.errors: list[str] = []  # Track substitution errors
        # Pipeline checks this to decide whether to run restore_placeholders.
        # Always True: restore is idempotent (no-op when no placeholders).
        self.escaped_placeholders = True

    def update_context(self, context: dict[str, Any]) -> None:
        """
        Update the rendering context (for parser reuse).

        Args:
            context: New context dict with variables (page, site, config, etc.)
        """
        self.context = context
        self.errors = []  # Reset errors for new page

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
            return self._literal_placeholder(expr)

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
                return self._literal_placeholder(f" {expr} ")

            try:
                # Evaluate expression in context
                result = self._eval_expression(expr)
                if result is None:
                    return self._literal_placeholder(f" {expr} ")
                return str(result)
            except Exception as e:
                # On error, keep as placeholder for documentation display
                msg = f"{expr}: {e}"
                self.errors.append(msg)
                logger.warning(
                    "variable_substitution_failed",
                    expression=expr,
                    error=str(e),
                    error_type=type(e).__name__,
                    action="keeping_as_placeholder",
                )
                return self._literal_placeholder(f" {expr} ")

        return self.VARIABLE_PATTERN.sub(replace_var, text)

    def substitute_inline_markdown(self, text: str) -> str:
        """
        Substitute variables in inline markdown while preserving code spans.

        Patitas needs live values before inline parsing so constructs like
        ``[Docs]({{ page.href }})`` can still become real links. This scanner
        rewrites only the plain-text segments between backtick code spans.
        """
        if "`" not in text:
            return self.substitute_variables(text)

        parts: list[str] = []
        text_start = 0
        pos = 0
        text_len = len(text)

        while pos < text_len:
            if text[pos] != "`":
                pos += 1
                continue

            count = 1
            while pos + count < text_len and text[pos + count] == "`":
                count += 1

            delimiter = "`" * count
            close_pos = text.find(delimiter, pos + count)
            if close_pos == -1:
                pos += count
                continue

            if text_start < pos:
                parts.append(self.substitute_variables(text[text_start:pos]))

            parts.append(text[pos : close_pos + count])
            pos = close_pos + count
            text_start = pos

        if not parts:
            return self.substitute_variables(text)

        if text_start < text_len:
            parts.append(self.substitute_variables(text[text_start:]))

        return "".join(parts)

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
        return self.restore_static_placeholders(html)

    @classmethod
    def restore_static_placeholders(cls, html: str) -> str:
        """
        Restore stateless literal markers back to HTML-escaped template syntax.

        This supports both the AST-aware marker form and raw ``{{/* ... */}}``
        escape syntax so cached AST re-renders and direct content renders behave
        the same.
        """

        def restore_marker(match: Match[str]) -> str:
            return cls._html_escape_template(match.group(1))

        html = cls.LITERAL_MARKER_PATTERN.sub(restore_marker, html)
        html = cls.ESCAPE_PATTERN.sub(lambda match: cls._html_escape_template(match.group(1)), html)
        return html

    @classmethod
    def _literal_placeholder(cls, inner: str) -> str:
        """Encode literal template syntax using fixed-width stateless markers."""
        return f"{cls.LITERAL_MARKER_START}{inner}{cls.LITERAL_MARKER_END}"

    @staticmethod
    def _html_escape_template(inner: str) -> str:
        """Render template syntax as HTML entities for literal display."""
        return f"&#123;&#123;{inner}&#125;&#125;"

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
        from bengal.errors import BengalRenderingError, ErrorCode

        for part in parts:
            if part.startswith("_"):
                raise BengalRenderingError(
                    f"Access to private/protected attributes denied: '{part}' in '{expr}'",
                    suggestion="Use public attributes only in template expressions",
                    code=ErrorCode.R003,
                )

        result: Any = self.context

        for part in parts:
            # SECURITY: Double-check dunder blocking on actual attribute access
            if part.startswith("_"):
                raise BengalRenderingError(
                    f"Access to private/protected attributes denied: '{part}'",
                    suggestion="Use public attributes only in template expressions",
                    code=ErrorCode.R003,
                )

            # Preference: Dictionary keys take precedence over methods/attributes
            # This prevents {{ items }} returning the dict.items() method instead of the value.
            if isinstance(result, dict) and part in result:
                result = result[part]
            elif hasattr(result, part):
                result = getattr(result, part)
            elif isinstance(result, dict):
                # Fallback for get() if we want to allow None (though _eval_expression usually raises)
                result = result.get(part)
                if result is None:
                    raise BengalRenderingError(
                        f"Key '{part}' not found in expression '{expr}'",
                        suggestion=f"Check that '{part}' exists in the context dictionary",
                        code=ErrorCode.R003,
                    )
            else:
                raise BengalRenderingError(
                    f"Cannot access '{part}' in expression '{expr}'",
                    suggestion=f"'{part}' is not a valid attribute or key for this object",
                    code=ErrorCode.R003,
                )

        return result
