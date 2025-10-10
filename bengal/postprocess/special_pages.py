"""
Special pages generation for Bengal SSG.

Handles generation of special pages that don't come from markdown content:
- 404 error page
- search page (future)
- other static utility pages
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from bengal.core.site import Site


class SpecialPagesGenerator:
    """
    Generates special pages like 404, search, etc.
    
    These pages use templates from the theme but don't have corresponding
    markdown source files. They need to be rendered during the build process
    to ensure they have proper styling and navigation.
    
    Currently generates:
    - 404.html: Custom 404 error page with site styling
    
    Future:
    - search.html: Client-side search page
    - sitemap.html: Human-readable sitemap
    """
    
    def __init__(self, site: 'Site') -> None:
        """
        Initialize special pages generator.
        
        Args:
            site: Site instance with configuration and template engine
        """
        self.site = site
    
    def generate(self) -> None:
        """
        Generate all special pages that are enabled.
        
        Currently only generates 404 page if 404.html template exists in theme.
        Failures are logged but don't stop the build process.
        """
        pages_generated = []
        
        # Always generate 404 page
        if self._generate_404():
            pages_generated.append('404')
        
        # Detailed output removed - postprocess phase summary is sufficient
        # Individual task output clutters the build log
        pass
    
    def _generate_404(self) -> bool:
        """
        Generate 404 error page with site styling.
        
        Uses 404.html template from theme if it exists. Creates a minimal
        page context and renders the template with site navigation and styling.
        
        Returns:
            True if generated successfully, False if template missing or error occurred
        
        Note:
            Errors are logged but don't fail the build - a missing 404 page
            is not critical for site functionality
        """
        try:
            from bengal.rendering.template_engine import TemplateEngine
            
            # Get template engine (reuse site's if available)
            if hasattr(self.site, 'template_engine'):
                template_engine = self.site.template_engine
            else:
                # Create new template engine for rendering
                template_engine = TemplateEngine(self.site)
            
            # Check if 404.html template exists
            try:
                template_engine.env.get_template('404.html')
            except Exception:
                # No 404 template in theme, skip generation
                return False
            
            # Create context for 404 page
            # Create a minimal page-like object for template context
            from types import SimpleNamespace
            
            page_context = SimpleNamespace(
                title='Page Not Found',
                url='/404.html',
                kind='page',
                draft=False,
                metadata={},
                tags=[],
                content='',
            )
            
            context = {
                'site': self.site,
                'page': page_context,
                'config': self.site.config,
            }
            
            # Render 404 page (template functions are already registered in TemplateEngine.__init__)
            rendered_html = template_engine.render('404.html', context)
            
            # Write to output directory
            output_path = self.site.output_dir / '404.html'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            
            return True
            
        except Exception as e:
            logger.error("404_page_generation_failed",
                        error=str(e),
                        error_type=type(e).__name__)
            return False

