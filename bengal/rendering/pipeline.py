"""
Rendering Pipeline - Orchestrates the parsing, AST building, templating, and output rendering.
"""

import threading
from pathlib import Path
from typing import Any, Optional

from bengal.core.page import Page
from bengal.rendering.parser import create_markdown_parser, BaseMarkdownParser
from bengal.rendering.template_engine import TemplateEngine
from bengal.rendering.renderer import Renderer
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


# Thread-local storage for parser instances (reuse parsers per thread)
_thread_local = threading.local()

# Cache for created directories (reduces syscalls in parallel builds)
_created_dirs = set()
_created_dirs_lock = threading.Lock()


def _get_thread_parser(engine: Optional[str] = None) -> BaseMarkdownParser:
    """
    Get or create a MarkdownParser instance for the current thread.
    
    Thread-Local Caching Strategy:
        - Creates ONE parser per worker thread (expensive operation ~10ms)
        - Caches it for the lifetime of that thread
        - Each thread reuses its parser for all pages it processes
        - Total parsers created = number of worker threads
    
    Performance Impact:
        With max_workers=N (from config):
        - N worker threads created
        - N parser instances created (one per thread)
        - Each parser handles ~(total_pages / N) pages
        
        Example with max_workers=10 and 200 pages:
        - 10 threads → 10 parsers created
        - Each parser processes ~20 pages
        - Creation cost: 10ms × 10 = 100ms one-time
        - Reuse savings: 9.9 seconds (avoiding 190 × 10ms)
    
    Thread Safety:
        Each thread gets its own parser instance, no locking needed.
        Read-only access to site config and xref_index is safe.
    
    Args:
        engine: Parser engine to use ('python-markdown', 'mistune', or None for default)
    
    Returns:
        Cached MarkdownParser instance for this thread
        
    Note:
        If you see N parser instances created where N = max_workers,
        this is OPTIMAL behavior, not a bug!
    """
    # Store parser per engine type
    cache_key = f'parser_{engine or "default"}'
    if not hasattr(_thread_local, cache_key):
        setattr(_thread_local, cache_key, create_markdown_parser(engine))
    return getattr(_thread_local, cache_key)


class RenderingPipeline:
    """
    Coordinates the entire rendering process for content.
    
    Pipeline stages:
    1. Parse source content (Markdown, etc.)
    2. Build Abstract Syntax Tree (AST)
    3. Apply templates
    4. Render output (HTML)
    5. Write to output directory
    """
    
    def __init__(self, site: Any, dependency_tracker: Any = None, quiet: bool = False, build_stats: Any = None) -> None:
        """
        Initialize the rendering pipeline.
        
        Parser Selection:
            Reads from config in this order:
            1. config['markdown_engine'] (legacy)
            2. config['markdown']['parser'] (preferred)
            3. Default: 'python-markdown'
            
            Common values:
            - 'mistune': Fast parser, recommended for most sites
            - 'python-markdown': Full-featured, slightly slower
        
        Parser Caching:
            Uses thread-local caching via _get_thread_parser().
            Creates ONE parser per worker thread, cached for reuse.
            
            With max_workers=N:
            - First page in thread: creates parser (~10ms)
            - Subsequent pages: reuses cached parser (~0ms)
            - Total parsers = N (optimal)
        
        Cross-Reference Support:
            If site has xref_index (built during discovery):
            - Enables [[link]] syntax in markdown
            - Enables automatic .md link resolution (future)
            - O(1) lookup performance
        
        Args:
            site: Site instance with config and xref_index
            dependency_tracker: Optional tracker for incremental builds
            quiet: If True, suppress per-page output
            build_stats: Optional BuildStats object to collect warnings
            
        Note:
            Each worker thread creates its own RenderingPipeline instance.
            The parser is cached at thread level, not pipeline level.
        """
        self.site = site
        # Get markdown engine from config (default: python-markdown)
        # Check both old location (markdown_engine) and new nested location (markdown.parser)
        markdown_engine = site.config.get('markdown_engine')
        if not markdown_engine:
            # Check nested markdown section
            markdown_config = site.config.get('markdown', {})
            markdown_engine = markdown_config.get('parser', 'python-markdown')
        # Use thread-local parser to avoid re-initialization overhead
        self.parser = _get_thread_parser(markdown_engine)
        
        # Enable cross-references if xref_index is available
        if hasattr(site, 'xref_index') and hasattr(self.parser, 'enable_cross_references'):
            self.parser.enable_cross_references(site.xref_index)
        
        self.dependency_tracker = dependency_tracker
        self.quiet = quiet
        self.build_stats = build_stats
        self.template_engine = TemplateEngine(site)
        if self.dependency_tracker:
            self.template_engine._dependency_tracker = self.dependency_tracker
        self.renderer = Renderer(self.template_engine, build_stats=build_stats)
    
    def process_page(self, page: Page) -> None:
        """
        Process a single page through the entire pipeline.
        
        Args:
            page: Page to process
        """
        # Track this page if we have a dependency tracker
        if self.dependency_tracker and not page.metadata.get('_generated'):
            self.dependency_tracker.start_page(page.source_path)
        
        # Stage 0: Determine output path early so page.url works correctly
        if not page.output_path:
            page.output_path = self._determine_output_path(page)
        
        # OPTIMIZATION #2: Try parsed content cache first
        # Skip markdown parsing if we have cached HTML and only template changed
        template = self._determine_template(page)
        parser_version = self._get_parser_version()
        
        if self.dependency_tracker and hasattr(self.dependency_tracker, '_cache'):
            cache = self.dependency_tracker._cache
            if cache and not page.metadata.get('_generated'):
                cached = cache.get_parsed_content(
                    page.source_path,
                    page.metadata,
                    template,
                    parser_version
                )
                
                if cached:
                    # Cache HIT - skip markdown parsing!
                    page.parsed_ast = cached['html']
                    page.toc = cached['toc']
                    page._toc_items_cache = cached.get('toc_items', [])
                    
                    # Track cache hit for statistics
                    if self.build_stats:
                        if not hasattr(self.build_stats, 'parsed_cache_hits'):
                            self.build_stats.parsed_cache_hits = 0
                        self.build_stats.parsed_cache_hits += 1
                    
                    # Continue to template rendering (skipped parsing, will apply current template)
                    # Note: We don't return early - we need to apply the template
                    parsed_content = cached['html']
                    
                    # Skip to stage 3 (template rendering)
                    page.extract_links()
                    html_content = self.renderer.render_content(parsed_content)
                    page.rendered_html = self.renderer.render_page(page, html_content)
                    self._write_output(page)
                    
                    if self.dependency_tracker and not page.metadata.get('_generated'):
                        self.dependency_tracker.end_page()
                    
                    return  # EARLY RETURN - parsing skipped, template applied!
        
        # Stage 1 & 2: Parse content with variable substitution
        # 
        # ARCHITECTURE: Clean separation of concerns
        # - Mistune parser: Handles {{ vars }} via VariableSubstitutionPlugin
        # - Templates: Handle {% if %}, {% for %}, complex logic
        # - Code blocks: Naturally stay literal (AST-level operation)
        #
        # Pages can disable preprocessing by setting `preprocess: false` in frontmatter.
        # This is useful for documentation pages that show template syntax examples.
        #
        if hasattr(self.parser, 'parse_with_toc_and_context'):
            # Mistune with VariableSubstitutionPlugin (recommended)
            # Check if preprocessing is disabled
            if page.metadata.get('preprocess') is False:
                # Parse without variable substitution (for docs showing template syntax)
                parsed_content, toc = self.parser.parse_with_toc(
                    page.content,
                    page.metadata
                )
            else:
                # Single-pass parsing with variable substitution - fast and simple!
                context = {
                    'page': page,
                    'site': self.site,
                    'config': self.site.config
                }
                parsed_content, toc = self.parser.parse_with_toc_and_context(
                    page.content,
                    page.metadata,
                    context
                )
        else:
            # FALLBACK: python-markdown (legacy)
            # Uses Jinja2 preprocessing - deprecated, use Mistune instead
            content = self._preprocess_content(page)
            parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        
        page.parsed_ast = parsed_content
        
        # Post-process: Enhance API documentation with badges
        # (inject HTML badges for @async, @property, etc. markers)
        from bengal.rendering.api_doc_enhancer import get_enhancer
        enhancer = get_enhancer()
        page_type = page.metadata.get('type')
        if enhancer.should_enhance(page_type):
            before_enhancement = page.parsed_ast
            page.parsed_ast = enhancer.enhance(page.parsed_ast, page_type)
            
            # Debug output only in dev mode
            from bengal.utils.profile import should_show_debug
            if should_show_debug() and '@property' in before_enhancement and 'page.md' in str(page.source_path) and 'core' in str(page.source_path):
                logger.debug("api_doc_enhancement",
                            source_path=str(page.source_path),
                            before_chars=len(before_enhancement),
                            after_chars=len(page.parsed_ast),
                            has_markers=('@property' in before_enhancement),
                            has_badges=('api-badge' in page.parsed_ast))
        
        # ============================================================================
        # Build Phase: PARSING COMPLETE
        # ============================================================================
        # At this point:
        # - page.parsed_ast contains HTML (post-markdown, pre-template)
        # - page.toc contains TOC HTML
        # - page.toc_items property can now extract structured TOC data
        #
        # Note: toc_items is a lazy @property that:
        # - Returns [] if accessed before this point (doesn't cache empty)
        # - Extracts and caches structure when accessed after this point
        # ============================================================================
        page.toc = toc
        
        # OPTIMIZATION #2: Store parsed content in cache for next build
        if self.dependency_tracker and hasattr(self.dependency_tracker, '_cache'):
            cache = self.dependency_tracker._cache
            if cache and not page.metadata.get('_generated'):
                # Extract TOC items for caching
                toc_items = extract_toc_structure(toc)
                
                cache.store_parsed_content(
                    page.source_path,
                    parsed_content,
                    toc,
                    toc_items,
                    page.metadata,
                    template,
                    parser_version
                )
        
        # Stage 3: Extract links for validation
        page.extract_links()
        
        # Stage 4: Render content to HTML
        html_content = self.renderer.render_content(parsed_content)
        
        # Stage 5: Apply template (with dependency tracking already set in __init__)
        page.rendered_html = self.renderer.render_page(page, html_content)
        
        # Stage 6: Write output
        self._write_output(page)
        
        # End page tracking
        if self.dependency_tracker and not page.metadata.get('_generated'):
            self.dependency_tracker.end_page()
    
    def _write_output(self, page: Page) -> None:
        """
        Write rendered page to output directory.
        
        Args:
            page: Page with rendered content
        """
        # Ensure parent directory exists (with caching to reduce syscalls)
        parent_dir = page.output_path.parent
        
        # Only create directory if not already done (thread-safe check)
        if parent_dir not in _created_dirs:
            with _created_dirs_lock:
                # Double-check inside lock to avoid race condition
                if parent_dir not in _created_dirs:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                    _created_dirs.add(parent_dir)
        
        # Write rendered HTML atomically (crash-safe)
        from bengal.utils.atomic_write import atomic_write_text
        atomic_write_text(page.output_path, page.rendered_html, encoding='utf-8')
        
        # Only print in verbose mode
        if not self.quiet:
            print(f"  ✓ {page.output_path.relative_to(self.site.output_dir)}")
    
    def _determine_output_path(self, page: Page) -> Path:
        """
        Determine the output path for a page.
        
        Args:
            page: Page to determine path for
            
        Returns:
            Output path
        """
        # Get relative path from content directory
        content_dir = self.site.root_path / "content"
        
        try:
            rel_path = page.source_path.relative_to(content_dir)
        except ValueError:
            # If not under content_dir, use just the filename
            rel_path = Path(page.source_path.name)
        
        # Change extension to .html
        output_rel_path = rel_path.with_suffix('.html')
        
        # Handle index pages specially (index.md and _index.md → index.html)
        # Others can optionally use pretty URLs (about.md → about/index.html)
        if self.site.config.get("pretty_urls", True) and output_rel_path.stem not in ("index", "_index"):
            output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        elif output_rel_path.stem == "_index":
            # _index.md should become index.html in the same directory
            output_rel_path = output_rel_path.parent / "index.html"
        
        return self.site.output_dir / output_rel_path
    
    def _determine_template(self, page: Page) -> str:
        """
        Determine which template will be used for this page.
        
        Args:
            page: Page object
            
        Returns:
            Template name (e.g., 'single.html', 'page.html')
        """
        # Check page-specific template first
        if hasattr(page, 'template') and page.template:
            return page.template
        
        # Check metadata
        if 'template' in page.metadata:
            return page.metadata['template']
        
        # Default based on page type
        page_type = page.metadata.get('type', 'page')
        
        if page_type == 'page':
            return 'page.html'
        elif page_type == 'section' or page.metadata.get('is_section'):
            return 'list.html'
        else:
            return 'single.html'
    
    def _get_parser_version(self) -> str:
        """
        Get parser version string for cache validation.
        
        Includes both parser library version and TOC extraction version to
        invalidate cache when TOC parsing logic changes.
        
        Returns:
            Parser version (e.g., "mistune-3.0-toc2", "markdown-3.4-toc2")
        """
        parser_name = type(self.parser).__name__
        
        # Try to get actual version
        if parser_name == 'MistuneParser':
            try:
                import mistune
                base_version = f"mistune-{mistune.__version__}"
            except (ImportError, AttributeError):
                base_version = "mistune-unknown"
        elif parser_name == 'PythonMarkdownParser':
            try:
                import markdown
                base_version = f"markdown-{markdown.__version__}"
            except (ImportError, AttributeError):
                base_version = "markdown-unknown"
        else:
            base_version = f"{parser_name}-unknown"
        
        # Add TOC extraction version to invalidate cache when extraction logic changes
        return f"{base_version}-toc{TOC_EXTRACTION_VERSION}"
    
    def _preprocess_content(self, page: Page) -> str:
        """
        Pre-process page content through Jinja2 to allow variable substitution.
        
        This allows technical writers to use {{ page.metadata.xxx }} directly
        in their markdown content, not just in templates.
        
        Pages can disable preprocessing by setting `preprocess: false` in frontmatter.
        This is useful for documentation pages that show Jinja2 syntax examples.
        
        Args:
            page: Page to pre-process
            
        Returns:
            Content with Jinja2 variables rendered
            
        Example:
            # In markdown:
            Today we're talking about {{ page.metadata.product_name }} 
            version {{ page.metadata.version }}.
        """
        # Skip preprocessing if disabled in frontmatter
        if page.metadata.get('preprocess') is False:
            return page.content
        
        from jinja2 import Template, TemplateSyntaxError
        
        try:
            # Create a Jinja2 template from the content
            template = Template(page.content)
            
            # Render with page and site context
            rendered_content = template.render(
                page=page,
                site=self.site,
                config=self.site.config
            )
            
            return rendered_content
            
        except TemplateSyntaxError as e:
            # If there's a syntax error, warn but continue with original content
            if self.build_stats:
                self.build_stats.add_warning(str(page.source_path), str(e), 'jinja2')
            else:
                logger.warning("jinja2_syntax_error",
                              source_path=str(page.source_path),
                              error=str(e),
                              error_type=type(e).__name__)
            if not self.quiet and not self.build_stats:
                print(f"  ⚠️  Jinja2 syntax error in {page.source_path}: {e}")
            return page.content
        except Exception as e:
            # For any other error, warn but continue
            if self.build_stats:
                self.build_stats.add_warning(str(page.source_path), str(e), 'preprocessing')
            else:
                logger.warning("preprocessing_error",
                              source_path=str(page.source_path),
                              error=str(e),
                              error_type=type(e).__name__)
            if not self.quiet and not self.build_stats:
                print(f"  ⚠️  Error pre-processing {page.source_path}: {e}")
            return page.content


# TOC extraction version - increment when extract_toc_structure() logic changes
TOC_EXTRACTION_VERSION = "2"  # v2: Added regex-based indentation parsing for mistune

def extract_toc_structure(toc_html: str) -> list:
    """
    Parse TOC HTML into structured data for custom rendering.
    
    Handles both nested <ul> structures (python-markdown style) and flat lists (mistune style).
    For flat lists from mistune, parses indentation to infer heading levels.
    
    This is a standalone function so it can be called from Page.toc_items
    property for lazy evaluation.
    
    Args:
        toc_html: HTML table of contents
        
    Returns:
        List of TOC items with id, title, and level (1=H2, 2=H3, 3=H4, etc.)
    """
    if not toc_html:
        return []
    
    import re
    
    try:
        # For mistune's flat TOC with indentation, use regex to preserve whitespace
        # Pattern: optional spaces + <li><a href="#id">title</a></li>
        pattern = r'^(\s*)<li><a href="#([^"]+)">([^<]+)</a></li>'
        
        items = []
        for line in toc_html.split('\n'):
            match = re.match(pattern, line)
            if match:
                indent_str, anchor_id, title = match.groups()
                # Count spaces to determine level (mistune uses 2 spaces per level)
                indent_level = len(indent_str)
                level = (indent_level // 2) + 1  # 0 spaces = level 1 (H2), 2 spaces = level 2 (H3), etc.
                
                items.append({
                    'id': anchor_id,
                    'title': title,
                    'level': level
                })
        
        if items:
            return items
        
        # Fallback to HTML parser for nested structures (python-markdown style)
        from html.parser import HTMLParser
        
        class TOCParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.items = []
                self.current_item = None
                self.depth = 0
            
            def handle_starttag(self, tag, attrs):
                if tag == 'ul':
                    self.depth += 1
                elif tag == 'a':
                    attrs_dict = dict(attrs)
                    self.current_item = {
                        'id': attrs_dict.get('href', '').lstrip('#'),
                        'title': '',
                        'level': self.depth
                    }
            
            def handle_data(self, data):
                if self.current_item is not None:
                    self.current_item['title'] += data.strip()
            
            def handle_endtag(self, tag):
                if tag == 'ul':
                    self.depth -= 1
                elif tag == 'a' and self.current_item:
                    if self.current_item['title']:
                        self.items.append(self.current_item)
                    self.current_item = None
        
        parser = TOCParser()
        parser.feed(toc_html)
        return parser.items
        
    except Exception:
        # If parsing fails, return empty list
        return []

