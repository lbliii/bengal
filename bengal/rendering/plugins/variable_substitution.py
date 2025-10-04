"""
Variable substitution plugin for Mistune.

Provides safe {{ variable }} replacement in markdown content while keeping
code blocks literal and maintaining clear separation from template logic.
"""

import re
from typing import Any, Dict, Match

__all__ = ['VariableSubstitutionPlugin']


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
    
    VARIABLE_PATTERN = re.compile(r'\{\{\s*([^}]+)\s*\}\}')
    
    def __init__(self, context: Dict[str, Any]):
        """
        Initialize with rendering context.
        
        Args:
            context: Dict with variables (page, site, config, etc.)
        """
        self.context = context
        self.errors = []  # Track substitution errors
    
    def update_context(self, context: Dict[str, Any]) -> None:
        """
        Update the rendering context (for parser reuse).
        
        Args:
            context: New context dict with variables (page, site, config, etc.)
        """
        self.context = context
        self.errors = []  # Reset errors for new page
    
    def __call__(self, md):
        """Register the plugin with Mistune."""
        if md.renderer and md.renderer.NAME == 'html':
            # Store original text renderer
            original_text = md.renderer.text
            
            # Create wrapped renderer that substitutes variables
            def text_with_substitution(text: str) -> str:
                """Render text with variable substitution."""
                substituted = self._substitute_variables(text)
                return original_text(substituted)
            
            # Replace text renderer
            md.renderer.text = text_with_substitution
    
    def _substitute_variables(self, text: str) -> str:
        """
        Substitute {{ variable }} expressions in text.
        
        Note: {% if %} blocks are handled by preprocessing, not here.
        
        Args:
            text: Raw text content
            
        Returns:
            Text with variables substituted
        """
        def replace_var(match: Match) -> str:
            expr = match.group(1).strip()
            try:
                # Evaluate expression in context
                result = self._eval_expression(expr)
                return str(result) if result is not None else match.group(0)
            except Exception:
                # On error, leave original syntax unchanged
                # This is intentional: allows documentation to show template syntax
                return match.group(0)
        
        return self.VARIABLE_PATTERN.sub(replace_var, text)
    
    def _eval_expression(self, expr: str) -> Any:
        """
        Safely evaluate a simple expression like 'page.metadata.title'.
        
        Supports dot notation for accessing nested attributes/dict keys.
        
        Args:
            expr: Expression to evaluate (e.g., 'page.metadata.title')
            
        Returns:
            Evaluated result
            
        Raises:
            Exception: If evaluation fails
        """
        # Support simple dot notation: page.metadata.title
        parts = expr.split('.')
        result = self.context
        
        for part in parts:
            if hasattr(result, part):
                result = getattr(result, part)
            elif isinstance(result, dict):
                result = result.get(part)
                if result is None:
                    raise ValueError(f"Key '{part}' not found in expression '{expr}'")
            else:
                raise ValueError(f"Cannot access '{part}' in expression '{expr}'")
        
        return result

