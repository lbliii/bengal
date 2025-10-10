"""
Rubric directive for Mistune.

Provides styled text that looks like a heading but isn't part of the
document hierarchy or table of contents. Perfect for API documentation
section labels like "Parameters:", "Returns:", "Raises:", etc.
"""

from mistune.directives import DirectivePlugin

__all__ = ['RubricDirective', 'render_rubric']


class RubricDirective(DirectivePlugin):
    """
    Rubric directive for pseudo-headings.
    
    Syntax:
        ```{rubric} Parameters
        ```
        
        ```{rubric} Returns
        :class: api-returns
        ```
    
    Creates styled text that looks like a heading but doesn't appear in TOC.
    """
    
    def parse(self, block, m, state):
        """Parse rubric directive."""
        title = self.parse_title(m)
        if not title:
            title = ''
        
        options = dict(self.parse_options(m))
        content = self.parse_content(m)
        
        # Parse any content (should be empty for rubrics)
        children = self.parse_tokens(block, content, state)
        
        return {
            'type': 'rubric',
            'attrs': {
                'title': title,
                'class': options.get('class', ''),
            },
            'children': children
        }
    
    def __call__(self, directive, md):
        """Register the directive and renderer."""
        directive.register('rubric', self.parse)
        
        if md.renderer and md.renderer.NAME == 'html':
            md.renderer.register('rubric', render_rubric)


def render_rubric(renderer, text, **attrs) -> str:
    """
    Render rubric to HTML.
    
    Renders as a styled div that looks like a heading but is
    semantically different (not part of document outline).
    
    Args:
        renderer: Mistune renderer
        text: Rendered children content (unused for rubrics)
        **attrs: Directive attributes (title, class, etc.)
    """
    title = attrs.get('title', '')
    css_class = attrs.get('class', '')
    
    # Build class list
    classes = ['rubric']
    if css_class:
        classes.append(css_class)
    
    class_attr = ' '.join(classes)
    
    html = f'<div class="{class_attr}" role="heading" aria-level="5">{title}</div>\n'
    
    return html

