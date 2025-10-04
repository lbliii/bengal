"""
Template engine using Jinja2.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from bengal.rendering.template_functions import register_all


class TemplateEngine:
    """
    Template engine for rendering pages with Jinja2 templates.
    """
    
    def __init__(self, site: Any) -> None:
        """
        Initialize the template engine.
        
        Args:
            site: Site instance
        """
        self.site = site
        self.template_dirs = []  # Initialize before _create_environment populates it
        self.env = self._create_environment()  # This will populate self.template_dirs
        self._dependency_tracker = None  # Set by RenderingPipeline for incremental builds (private attr)
    
    def _create_environment(self) -> Environment:
        """
        Create and configure Jinja2 environment.
        
        Returns:
            Configured Jinja2 environment
        """
        # Look for templates in multiple locations
        template_dirs = []
        
        # Custom templates directory
        custom_templates = self.site.root_path / "templates"
        if custom_templates.exists():
            template_dirs.append(str(custom_templates))
        
        # Theme templates
        if self.site.theme:
            theme_templates = self.site.root_path / "themes" / self.site.theme / "templates"
            if theme_templates.exists():
                template_dirs.append(str(theme_templates))
        
        # Default templates (bundled with Bengal)
        default_templates = Path(__file__).parent.parent / "themes" / "default" / "templates"
        if default_templates.exists():
            template_dirs.append(str(default_templates))
        
        # Store for dependency tracking (convert back to Path objects)
        self.template_dirs = [Path(d) for d in template_dirs]
        
        # Create environment
        env = Environment(
            loader=FileSystemLoader(template_dirs) if template_dirs else FileSystemLoader('.'),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Add custom filters (legacy)
        env.filters['dateformat'] = self._filter_dateformat
        
        # Add global functions (legacy)
        env.globals['url_for'] = self._url_for
        env.globals['asset_url'] = self._asset_url
        env.globals['get_menu'] = self._get_menu
        
        # Register all template functions (Phase 1: 30 functions)
        register_all(env, self.site)
        
        return env
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Template context variables
            
        Returns:
            Rendered HTML
        """
        # Track template dependency
        if self._dependency_tracker:
            template_path = self._find_template_path(template_name)
            if template_path:
                self._dependency_tracker.track_template(template_path)
        
        # Add site to context
        context.setdefault('site', self.site)
        context.setdefault('config', self.site.config)
        
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with the given context.
        
        Args:
            template_string: Template content as string
            context: Template context variables
            
        Returns:
            Rendered HTML
        """
        context.setdefault('site', self.site)
        context.setdefault('config', self.site.config)
        
        template = self.env.from_string(template_string)
        return template.render(**context)
    
    def _filter_dateformat(self, date: Any, format: str = '%Y-%m-%d') -> str:
        """
        Format a date using strftime.
        
        Args:
            date: Date to format
            format: strftime format string
            
        Returns:
            Formatted date string
        """
        if date is None:
            return ''
        
        try:
            return date.strftime(format)
        except (AttributeError, ValueError):
            return str(date)
    
    def _url_for(self, page: Any) -> str:
        """
        Generate URL for a page.
        
        Args:
            page: Page object
            
        Returns:
            URL path (clean, without index.html)
        """
        # Use the page's url property if available (clean URLs)
        if hasattr(page, 'url'):
            return page.url
        
        # Fallback to slug-based URL
        return f"/{page.slug}/"
    
    def _asset_url(self, asset_path: str) -> str:
        """
        Generate URL for an asset.
        
        Args:
            asset_path: Path to asset file
            
        Returns:
            Asset URL
        """
        return f"/assets/{asset_path}"
    
    def _get_menu(self, menu_name: str = 'main') -> list:
        """
        Get menu items as dicts for template access.
        
        Args:
            menu_name: Name of the menu to get (e.g., 'main', 'footer')
            
        Returns:
            List of menu item dicts
        """
        menu = self.site.menu.get(menu_name, [])
        return [item.to_dict() for item in menu]
    
    def _find_template_path(self, template_name: str) -> Optional[Path]:
        """
        Find the full path to a template file.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Full path to template file, or None if not found
        """
        for template_dir in self.template_dirs:
            template_path = template_dir / template_name
            if template_path.exists():
                return template_path
        return None
    

