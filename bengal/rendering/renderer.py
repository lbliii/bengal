"""
Renderer for converting pages to final HTML output.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import traceback

from bengal.core.page import Page


class Renderer:
    """
    Renders pages using templates.
    """
    
    def __init__(self, template_engine: Any) -> None:
        """
        Initialize the renderer.
        
        Args:
            template_engine: Template engine instance
        """
        self.template_engine = template_engine
        self.site = template_engine.site  # Access to site config for strict mode
    
    def render_content(self, content: str) -> str:
        """
        Render raw content (already parsed HTML).
        
        Args:
            content: Parsed HTML content
            
        Returns:
            Content (pass-through in this case)
        """
        return content
    
    def render_page(self, page: Page, content: Optional[str] = None) -> str:
        """
        Render a complete page with template.
        
        Args:
            page: Page to render
            content: Optional pre-rendered content (uses page.parsed_ast if not provided)
            
        Returns:
            Fully rendered HTML page
        """
        if content is None:
            content = page.parsed_ast or ""
        
        # Determine which template to use
        template_name = self._get_template_name(page)
        
        # Build base context
        context = {
            'page': page,
            'content': content,
            'title': page.title,
            'metadata': page.metadata,
        }
        
        # Add special context for generated pages
        if page.metadata.get('_generated'):
            self._add_generated_page_context(page, context)
        
        # Render with template
        try:
            return self.template_engine.render(template_name, context)
        except Exception as e:
            # In strict mode, fail loudly instead of falling back
            strict_mode = self.site.config.get("strict_mode", False)
            debug_mode = self.site.config.get("debug", False)
            
            if strict_mode:
                # Don't catch - let build fail with full error
                print(f"\n❌ ERROR: Failed to render page {page.source_path}")
                print(f"   Template: {template_name}")
                print(f"   Error: {e}")
                if debug_mode:
                    print("\nFull traceback:")
                    traceback.print_exc()
                raise
            
            # In production mode, warn and fall back gracefully
            print(f"⚠️  Warning: Failed to render page {page.source_path} with template {template_name}: {e}")
            
            if debug_mode:
                print("   Full traceback:")
                traceback.print_exc()
            
            # Fallback to simple HTML
            return self._render_fallback(page, content)
    
    def _add_generated_page_context(self, page: Page, context: Dict[str, Any]) -> None:
        """
        Add special context variables for generated pages (archives, tags, etc.).
        
        Args:
            page: Page being rendered
            context: Template context to update
        """
        page_type = page.metadata.get('type')
        
        if page_type == 'archive':
            # Archive page context
            section = page.metadata.get('_section')
            all_posts = page.metadata.get('_posts', [])
            paginator = page.metadata.get('_paginator')
            page_num = page.metadata.get('_page_num', 1)
            
            # Get posts for this page
            if paginator:
                posts = paginator.page(page_num)
                pagination = paginator.page_context(page_num, f"/{section.name}/")
            else:
                posts = sorted(all_posts, key=lambda p: p.date if p.date else datetime.min, reverse=True)
                pagination = {
                    'current_page': 1,
                    'total_pages': 1,
                    'has_next': False,
                    'has_prev': False,
                    'base_url': f"/{section.name}/" if section else "/",
                }
            
            context.update({
                'section': section,
                'posts': posts,
                'total_posts': len(all_posts),
                **pagination
            })
        
        elif page_type == 'tag':
            # Individual tag page context
            tag_name = page.metadata.get('_tag')
            tag_slug = page.metadata.get('_tag_slug')
            all_posts = page.metadata.get('_posts', [])
            paginator = page.metadata.get('_paginator')
            page_num = page.metadata.get('_page_num', 1)
            
            # Get posts for this page
            if paginator:
                posts = paginator.page(page_num)
                pagination = paginator.page_context(page_num, f"/tags/{tag_slug}/")
            else:
                posts = all_posts
                pagination = {
                    'current_page': 1,
                    'total_pages': 1,
                    'has_next': False,
                    'has_prev': False,
                    'base_url': f"/tags/{tag_slug}/",
                }
            
            context.update({
                'tag': tag_name,
                'tag_slug': tag_slug,
                'posts': posts,
                'total_posts': len(all_posts),
                **pagination
            })
        
        elif page_type == 'tag-index':
            # Tag index page context
            tags = page.metadata.get('_tags', {})
            
            # Convert to sorted list for template
            tags_list = [
                {
                    'name': data['name'],
                    'slug': data['slug'],
                    'count': len(data['pages']),
                    'pages': data['pages']
                }
                for data in tags.values()
            ]
            # Sort by count (descending) then name
            tags_list.sort(key=lambda t: (-t['count'], t['name'].lower()))
            
            context.update({
                'tags': tags_list,
                'total_tags': len(tags_list),
            })
    
    def _get_template_name(self, page: Page) -> str:
        """
        Determine which template to use for a page.
        
        Args:
            page: Page to get template for
            
        Returns:
            Template name
        """
        # Check page metadata for custom template
        if 'template' in page.metadata:
            return page.metadata['template']
        
        # Check page type
        page_type = page.metadata.get('type', 'page')
        
        # Map types to templates
        template_map = {
            'post': 'post.html',
            'page': 'page.html',
            'index': 'index.html',
        }
        
        return template_map.get(page_type, 'page.html')
    
    def _render_fallback(self, page: Page, content: str) -> str:
        """
        Render a simple fallback HTML page.
        
        Args:
            page: Page to render
            content: Page content
            
        Returns:
            Simple HTML page
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title}</title>
</head>
<body>
    <article>
        <h1>{page.title}</h1>
        {content}
    </article>
</body>
</html>
"""

