"""
Code tabs directive for Mistune.

Provides multi-language code examples with tabbed interface for easy
comparison across programming languages.
"""

import html as html_lib
import re

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = [
    'CodeTabsDirective',
    'render_code_tab_item',
    'render_code_tabs'
]

logger = get_logger(__name__)

# Pre-compiled regex patterns (compiled once, reused for all pages)
_CODE_TAB_SPLIT_PATTERN = re.compile(r'^### Tab: (.+)$', re.MULTILINE)
_CODE_BLOCK_EXTRACT_PATTERN = re.compile(r'```\w*\n(.*?)```', re.DOTALL)
_CODE_TAB_ITEM_PATTERN = re.compile(
    r'<div class="code-tab-item" data-lang="(.*?)" data-code="(.*?)"></div>',
    re.DOTALL
)


class CodeTabsDirective(DirectivePlugin):
    """
    Code tabs for multi-language examples.

    Syntax:
        ````{code-tabs}

        ### Tab: Python
        ```python
        # Example code here
        ```

        ### Tab: JavaScript
        ```javascript
        console.log("hello")
        ```
        ````
    """

    def parse(self, block, m, state):
        """Parse code tabs directive."""
        content = self.parse_content(m)

        # Split by tab markers (using pre-compiled pattern)
        parts = _CODE_TAB_SPLIT_PATTERN.split(content)

        tabs = []
        if len(parts) > 1:
            start_idx = 1 if not parts[0].strip() else 0

            for i in range(start_idx, len(parts), 2):
                if i + 1 < len(parts):
                    lang = parts[i].strip()
                    code_content = parts[i + 1].strip()

                    # Extract code from fenced block if present (using pre-compiled pattern)
                    code_match = _CODE_BLOCK_EXTRACT_PATTERN.search(code_content)
                    code = code_match.group(1).strip() if code_match else code_content

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
    tab_id = f'code-tabs-{id(text)}'

    # Extract code blocks from rendered text (using pre-compiled pattern)
    matches = _CODE_TAB_ITEM_PATTERN.findall(text)

    if not matches:
        return f'<div class="code-tabs">{text}</div>'

    # Build navigation
    nav_html = f'<div class="code-tabs" id="{tab_id}">\n  <ul class="tab-nav">\n'
    for i, (lang, _) in enumerate(matches):
        active = ' class="active"' if i == 0 else ''
        nav_html += f'    <li{active}><a href="#" data-tab-target="{tab_id}-{i}">{lang}</a></li>\n'
    nav_html += '  </ul>\n'

    # Build content
    content_html = '  <div class="tab-content">\n'
    for i, (lang, code) in enumerate(matches):
        active = ' active' if i == 0 else ''
        # HTML-decode the code
        code = html_lib.unescape(code)
        content_html += (
            f'    <div id="{tab_id}-{i}" class="tab-pane{active}">\n'
            f'      <pre><code class="language-{lang}">{code}</code></pre>\n'
            f'    </div>\n'
        )
    content_html += '  </div>\n</div>\n'

    return nav_html + content_html


def render_code_tab_item(renderer, **attrs):
    """Render code tab item marker (used internally)."""
    lang = attrs.get('lang', 'text')
    code = attrs.get('code', '')
    # HTML-escape the code for storage in data attribute
    code_escaped = html_lib.escape(code)
    return f'<div class="code-tab-item" data-lang="{lang}" data-code="{code_escaped}"></div>'

