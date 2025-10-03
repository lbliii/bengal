"""
Custom Mistune plugins for documentation features.

Provides:
- Admonitions (callout boxes) - Custom implementation
- Tabs - Custom directive
- Dropdowns - Custom directive  
- Code tabs - Custom directive
- Variable substitution - Safe {{ variable }} replacement in text only
- Note: Footnotes and def_list use Mistune's built-in plugins
"""

import re
from typing import Any, Dict, List, Match, Optional, Tuple
from mistune.directives import DirectivePlugin, FencedDirective


# =============================================================================
# VARIABLE SUBSTITUTION PLUGIN
# =============================================================================

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


# =============================================================================
# ADMONITION DIRECTIVE (Using Fenced Directive Syntax)
# =============================================================================

class AdmonitionDirective(DirectivePlugin):
    """
    Admonition directive using Mistune's fenced syntax.
    
    Syntax:
        ```{note} Optional Title
        Content with **markdown** support.
        ```
    
    Supported types: note, tip, warning, danger, error, info, example, success
    """
    
    ADMONITION_TYPES = [
        'note', 'tip', 'warning', 'danger', 'error', 
        'info', 'example', 'success', 'caution'
    ]
    
    def parse(self, block, m, state):
        """Parse admonition directive."""
        admon_type = self.parse_type(m)
        title = self.parse_title(m)
        
        # Use type as title if no title provided
        if not title:
            title = admon_type.capitalize()
        
        content = self.parse_content(m)
        
        # Parse nested markdown content
        children = self.parse_tokens(block, content, state)
        
        return {
            'type': 'admonition',
            'attrs': {
                'admon_type': admon_type,
                'title': title
            },
            'children': children
        }
    
    def __call__(self, directive, md):
        """Register all admonition types as directives."""
        for admon_type in self.ADMONITION_TYPES:
            directive.register(admon_type, self.parse)
        
        if md.renderer and md.renderer.NAME == 'html':
            md.renderer.register('admonition', render_admonition)


def render_admonition(renderer, text: str, admon_type: str, title: str) -> str:
    """Render admonition to HTML."""
    # Map types to CSS classes
    type_map = {
        'note': 'note',
        'tip': 'tip',
        'warning': 'warning',
        'caution': 'warning',
        'danger': 'danger',
        'error': 'error',
        'info': 'info',
        'example': 'example',
        'success': 'success',
    }
    
    css_class = type_map.get(admon_type, 'note')
    
    # text contains the rendered children
    html = (
        f'<div class="admonition {css_class}">\n'
        f'  <p class="admonition-title">{title}</p>\n'
        f'{text}'
        f'</div>\n'
    )
    return html


# =============================================================================
# CUSTOM DIRECTIVES FOR DOCUMENTATION (WITH NESTING SUPPORT)
# =============================================================================

class TabsDirective(DirectivePlugin):
    """
    Tabbed content directive with full markdown support.
    
    Syntax:
        ```{tabs}
        :id: my-tabs
        
        ### Tab: Python
        
        Content with **markdown**, code blocks, admonitions, etc.
        
        ### Tab: JavaScript
        
        More content here.
        ```
    
    Supports nested directives, code blocks, admonitions, etc.
    """
    
    def parse(self, block, m, state):
        """Parse tabs directive with nested content support."""
        options = dict(self.parse_options(m))
        content = self.parse_content(m)
        
        # Split content by tab markers: ### Tab: Title
        import re
        parts = re.split(r'^### Tab: (.+)$', content, flags=re.MULTILINE)
        
        tab_items = []
        if len(parts) > 1:
            # Skip first part if empty
            start_idx = 1 if not parts[0].strip() else 0
            
            if start_idx == 0:
                # No tab markers, treat as single tab
                tab_items.append({
                    'type': 'tab_title',
                    'text': options.get('title', 'Content')
                })
                tab_items.append({
                    'type': 'tab_content',
                    'children': self.parse_tokens(block, parts[0], state)
                })
            else:
                # Parse each tab
                for i in range(start_idx, len(parts), 2):
                    if i + 1 < len(parts):
                        title = parts[i].strip()
                        tab_content = parts[i + 1].strip()
                        
                        tab_items.append({
                            'type': 'tab_title',
                            'text': title
                        })
                        tab_items.append({
                            'type': 'tab_content',
                            'children': self.parse_tokens(block, tab_content, state)
                        })
        else:
            # No tab markers, treat entire content as one tab
            tab_items.append({
                'type': 'tab_title',
                'text': options.get('title', 'Content')
            })
            tab_items.append({
                'type': 'tab_content',
                'children': self.parse_tokens(block, content, state)
            })
        
        return {
            'type': 'tabs',
            'attrs': options,
            'children': tab_items
        }
    
    def __call__(self, directive, md):
        """Register the directive and renderers."""
        directive.register('tabs', self.parse)
        
        if md.renderer and md.renderer.NAME == 'html':
            md.renderer.register('tabs', render_tabs)
            md.renderer.register('tab_title', render_tab_title)
            md.renderer.register('tab_content', render_tab_content)


def render_tabs(renderer, text, **attrs):
    """Render tabs container to HTML.
    
    The text contains alternating tab titles and contents.
    We need to restructure this into navigation + content panes.
    """
    import re
    tab_id = attrs.get('id', f'tabs-{id(text)}')
    
    # Extract titles and contents from the rendered HTML
    # Pattern: <div class="tab-title">Title</div><div class="tab-content">Content</div>
    pattern = r'<div class="tab-title">(.*?)</div>\s*<div class="tab-content">(.*?)</div>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if not matches:
        # Fallback: just wrap the content
        return f'<div class="tabs" id="{tab_id}">\n{text}</div>\n'
    
    # Build navigation
    nav_html = f'<div class="tabs" id="{tab_id}">\n  <ul class="tab-nav">\n'
    for i, (title, _) in enumerate(matches):
        active = ' class="active"' if i == 0 else ''
        nav_html += f'    <li{active}><a href="#{tab_id}-{i}">{title.strip()}</a></li>\n'
    nav_html += '  </ul>\n'
    
    # Build content panes
    content_html = '  <div class="tab-content">\n'
    for i, (_, content) in enumerate(matches):
        active = ' active' if i == 0 else ''
        content_html += f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n{content}    </div>\n'
    content_html += '  </div>\n</div>\n'
    
    return nav_html + content_html


def render_tab_title(renderer, text):
    """Render tab title marker."""
    return f'<div class="tab-title">{text}</div>'


def render_tab_content(renderer, text):
    """Render tab content."""
    return f'<div class="tab-content">{text}</div>'


class DropdownDirective(DirectivePlugin):
    """
    Collapsible dropdown directive with markdown support.
    
    Syntax:
        ```{dropdown} Title
        :open: true
        
        Content with **markdown**, code blocks, etc.
        
        !!! note
            Even nested admonitions work!
        ```
    """
    
    def parse(self, block, m, state):
        """Parse dropdown directive with nested content support."""
        title = self.parse_title(m)
        if not title:
            title = 'Details'
        
        options = dict(self.parse_options(m))
        content = self.parse_content(m)
        
        # Parse nested markdown content
        children = self.parse_tokens(block, content, state)
        
        return {
            'type': 'dropdown',
            'attrs': {'title': title, **options},
            'children': children
        }
    
    def __call__(self, directive, md):
        """Register the directive and renderer."""
        directive.register('dropdown', self.parse)
        directive.register('details', self.parse)  # Alias
        
        if md.renderer and md.renderer.NAME == 'html':
            md.renderer.register('dropdown', render_dropdown)


def render_dropdown(renderer, text, **attrs):
    """Render dropdown to HTML."""
    title = attrs.get('title', 'Details')
    is_open = attrs.get('open', '').lower() in ('true', '1', 'yes')
    open_attr = ' open' if is_open else ''
    
    html = (
        f'<details class="dropdown"{open_attr}>\n'
        f'  <summary>{title}</summary>\n'
        f'  <div class="dropdown-content">\n'
        f'{text}'
        f'  </div>\n'
        f'</details>\n'
    )
    return html


class CodeTabsDirective(DirectivePlugin):
    """
    Code tabs for multi-language examples.
    
    Syntax:
        ```{code-tabs}
        
        ### Tab: Python
        ```python
        print("hello")
        ```
        
        ### Tab: JavaScript
        ```javascript
        console.log("hello")
        ```
        ```
    """
    
    def parse(self, block, m, state):
        """Parse code tabs directive."""
        content = self.parse_content(m)
        
        # Split by tab markers
        import re
        parts = re.split(r'^### Tab: (.+)$', content, flags=re.MULTILINE)
        
        tabs = []
        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0
            
            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    lang = parts[i].strip()
                    code_content = parts[i + 1].strip()
                    
                    # Extract code from fenced block if present
                    code_match = re.search(r'```\w*\n(.*?)```', code_content, re.DOTALL)
                    if code_match:
                        code = code_match.group(1).strip()
                    else:
                        code = code_content
                    
                    tabs.append({
                        'type': 'code_tab_item',
                        'attrs': {'lang': lang, 'code': code}
                    })
        
        return {
            'type': 'code_tabs',
            'children': tabs
        }
    
    def __call__(self, directive, md):
        """Register the directive and renderers."""
        directive.register('code-tabs', self.parse)
        directive.register('code_tabs', self.parse)  # Alias
        
        if md.renderer and md.renderer.NAME == 'html':
            md.renderer.register('code_tabs', render_code_tabs)
            md.renderer.register('code_tab_item', render_code_tab_item)


def render_code_tabs(renderer, text, **attrs):
    """Render code tabs to HTML."""
    import re
    tab_id = f'code-tabs-{id(text)}'
    
    # Extract code blocks from rendered text
    # Pattern: <div class="code-tab-item" data-lang="..." data-code="..."></div>
    pattern = r'<div class="code-tab-item" data-lang="(.*?)" data-code="(.*?)"></div>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if not matches:
        return f'<div class="code-tabs">{text}</div>'
    
    # Build navigation
    nav_html = f'<div class="code-tabs" id="{tab_id}">\n  <ul class="tab-nav">\n'
    for i, (lang, _) in enumerate(matches):
        active = ' class="active"' if i == 0 else ''
        nav_html += f'    <li{active}><a href="#{tab_id}-{i}">{lang}</a></li>\n'
    nav_html += '  </ul>\n'
    
    # Build content
    content_html = '  <div class="tab-content">\n'
    for i, (lang, code) in enumerate(matches):
        active = ' active' if i == 0 else ''
        # HTML-decode the code
        import html
        code = html.unescape(code)
        content_html += (
            f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n'
            f'      <pre><code class="language-{lang}">{code}</code></pre>\n'
            f'    </div>\n'
        )
    content_html += '  </div>\n</div>\n'
    
    return nav_html + content_html


def render_code_tab_item(renderer, **attrs):
    """Render code tab item marker (used internally)."""
    import html
    lang = attrs.get('lang', 'text')
    code = attrs.get('code', '')
    # HTML-escape the code for storage in data attribute
    code_escaped = html.escape(code)
    return f'<div class="code-tab-item" data-lang="{lang}" data-code="{code_escaped}"></div>'


# =============================================================================
# DIRECTIVE PLUGIN COLLECTION
# =============================================================================

def plugin_documentation_directives(md):
    """
    Add all documentation directives to Mistune.
    
    Provides:
    - admonitions: note, tip, warning, danger, error, info, example, success
    - tabs: Tabbed content with full markdown support
    - dropdown: Collapsible sections with markdown
    - code-tabs: Code examples in multiple languages
    
    Raises:
        RuntimeError: If directive registration fails
        ImportError: If FencedDirective is not available
    """
    try:
        from mistune.directives import FencedDirective
    except ImportError as e:
        import sys
        print(f"Error: FencedDirective not available in mistune: {e}", file=sys.stderr)
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
        ])
        
        # Apply to markdown instance
        return directive(md)
    except Exception as e:
        import sys
        print(f"Error registering documentation directives: {e}", file=sys.stderr)
        raise RuntimeError(f"Failed to register directives plugin: {e}") from e

