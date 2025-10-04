"""
Tabs directive for Mistune.

Provides tabbed content sections with full markdown support including
nested directives, code blocks, and admonitions.
"""

import re
from mistune.directives import DirectivePlugin

__all__ = [
    'TabsDirective',
    'render_tabs',
    'render_tab_title',
    'render_tab_content'
]

# Pre-compiled regex patterns (compiled once, reused for all pages)
_TAB_SPLIT_PATTERN = re.compile(r'^### Tab: (.+)$', re.MULTILINE)
_TAB_EXTRACT_PATTERN = re.compile(
    r'<div class="tab-title">(.*?)</div>\s*<div class="tab-content">(.*?)</div>',
    re.DOTALL
)


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
        
        # Split content by tab markers: ### Tab: Title (using pre-compiled pattern)
        parts = _TAB_SPLIT_PATTERN.split(content)
        
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
    tab_id = attrs.get('id', f'tabs-{id(text)}')
    
    # Extract titles and contents from the rendered HTML (using pre-compiled pattern)
    matches = _TAB_EXTRACT_PATTERN.findall(text)
    
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

