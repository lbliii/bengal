"""
Renderer for converting pages to final HTML output.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import traceback
import re

from bengal.core.page import Page


class Renderer:
    """
    Renders pages using templates.
    """
    
    def __init__(self, template_engine: Any, build_stats: Any = None) -> None:
        """
        Initialize the renderer.
        
        Args:
            template_engine: Template engine instance
            build_stats: Optional BuildStats object for error collection
        """
        self.template_engine = template_engine
        self.site = template_engine.site  # Access to site config for strict mode
        self.build_stats = build_stats  # For collecting template errors
    
    def render_content(self, content: str) -> str:
        """
        Render raw content (already parsed HTML).
        
        Automatically strips the first H1 tag to avoid duplication with
        the template-rendered title.
        
        Args:
            content: Parsed HTML content
            
        Returns:
            Content with first H1 removed
        """
        return self._strip_first_h1(content)
    
    def _strip_first_h1(self, content: str) -> str:
        """
        Remove the first H1 tag from HTML content.
        
        This prevents duplication when templates render {{ page.title }} as H1
        and the markdown also contains an H1 heading.
        
        Args:
            content: HTML content
            
        Returns:
            Content with first H1 tag removed
        """
        # Pattern matches: <h1>...</h1> or <h1 id="...">...</h1>
        # Uses non-greedy matching to get just the first H1
        pattern = r'<h1[^>]*>.*?</h1>'
        
        # Remove only the first occurrence
        result = re.sub(pattern, '', content, count=1, flags=re.DOTALL | re.IGNORECASE)
        
        return result
    
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
        
        # Mark active menu items for this page
        if hasattr(self.site, 'mark_active_menu_items'):
            self.site.mark_active_menu_items(page)
        
        # Determine which template to use
        template_name = self._get_template_name(page)
        
        # Build base context
        context = {
            'page': page,
            'content': content,
            'title': page.title,
            'metadata': page.metadata,
            'toc': page.toc,  # Table of contents HTML
            'toc_items': page.toc_items,  # Structured TOC data
        }
        
        # Add special context for generated pages
        if page.metadata.get('_generated'):
            self._add_generated_page_context(page, context)
        
        # Render with template
        try:
            return self.template_engine.render(template_name, context)
        except Exception as e:
            from bengal.rendering.errors import TemplateRenderError, display_template_error
            
            # Create rich error object
            rich_error = TemplateRenderError.from_jinja2_error(
                e,
                template_name,
                page.source_path,
                self.template_engine
            )
            
            # In strict mode, display and fail immediately
            strict_mode = self.site.config.get("strict_mode", False)
            debug_mode = self.site.config.get("debug", False)
            
            if strict_mode:
                display_template_error(rich_error)
                if debug_mode:
                    import traceback
                    traceback.print_exc()
                raise
            
            # In production mode, collect error and continue
            if self.build_stats:
                self.build_stats.add_template_error(rich_error)
            else:
                # No build stats available, display immediately
                display_template_error(rich_error)
            
            if debug_mode:
                import traceback
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
        
        Priority order:
        1. Explicit template in frontmatter (`template: doc.html`)
        2. Section-based auto-detection (e.g., `docs.html`, `docs/single.html`)
        3. Default fallback (`page.html` or `index.html`)
        
        Note: We intentionally avoid Hugo's confusing type/kind/layout hierarchy.
        
        Args:
            page: Page to get template for
            
        Returns:
            Template name
        """
        # 1. Explicit template (highest priority)
        if 'template' in page.metadata:
            return page.metadata['template']
        
        # 2. Section-based auto-detection
        if hasattr(page, '_section') and page._section:
            section_name = page._section.name
            is_section_index = page.source_path.stem == '_index'
            
            if is_section_index:
                # Try section index templates in order of specificity
                templates_to_try = [
                    f"{section_name}/list.html",      # Hugo-style directory
                    f"{section_name}/index.html",     # Alternative directory
                    f"{section_name}-list.html",      # Flat with suffix
                    f"{section_name}.html",           # Flat simple
                ]
            else:
                # Try section page templates in order of specificity
                templates_to_try = [
                    f"{section_name}/single.html",    # Hugo-style directory
                    f"{section_name}/page.html",      # Alternative directory
                    f"{section_name}.html",           # Flat
                ]
            
            # Check if any template exists
            for template_name in templates_to_try:
                if self._template_exists(template_name):
                    return template_name
        
        # 3. Simple default fallback (no type/kind complexity)
        if page.source_path.stem == '_index':
            # Section index without custom template
            return 'index.html'
        
        # Regular page - just use page.html
        return 'page.html'
    
    def _template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists in any template directory.
        
        Args:
            template_name: Template filename or path
            
        Returns:
            True if template exists, False otherwise
        """
        try:
            self.template_engine.env.get_template(template_name)
            return True
        except Exception:
            return False
    
    def _render_fallback(self, page: Page, content: str) -> str:
        """
        Render a fallback HTML page with basic styling.
        
        When the main template fails, we still try to produce a usable page
        with basic CSS and structure (though without partials/navigation).
        
        Args:
            page: Page to render
            content: Page content
            
        Returns:
            Fallback HTML page with minimal styling
        """
        # Try to include CSS if available
        css_link = ''
        if hasattr(self.site, 'output_dir'):
            css_file = self.site.output_dir / 'assets' / 'css' / 'style.css'
            if css_file.exists():
                css_link = '<link rel="stylesheet" href="/assets/css/style.css">'
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page.title} - {self.site.config.get('title', 'Site')}</title>
    {css_link}
    <style>
        /* Emergency fallback styling */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            color: #333;
        }}
        .fallback-notice {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            padding: 1rem;
            margin-bottom: 2rem;
        }}
        article {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
        }}
        h1 {{ color: #2c3e50; }}
        code {{ background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="fallback-notice">
        <strong>⚠️ Notice:</strong> This page is displayed in fallback mode due to a template error. 
        Some features (navigation, sidebars, etc.) may be missing.
    </div>
    <article>
        <h1>{page.title}</h1>
        {content}
    </article>
</body>
</html>
"""

