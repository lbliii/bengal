"""
Custom output formats generation (JSON, LLM text, etc.).

Generates alternative output formats for pages to enable:
- Client-side search (JSON index)
- AI/LLM discovery (plain text format)
- Programmatic access (JSON API)
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class OutputFormatsGenerator:
    """
    Generates custom output formats for pages.
    
    Provides alternative content formats to enable:
    - Client-side search via JSON index
    - AI/LLM discovery via plain text
    - Programmatic API access via JSON
    
    Output Formats:
    - Per-page JSON: page.json next to each page.html (metadata + content)
    - Per-page LLM text: page.txt next to each page.html (AI-friendly format)
    - Site-wide index.json: Searchable index of all pages with summaries
    - Site-wide llm-full.txt: Full site content in single text file
    
    Configuration (bengal.toml):
        [output_formats]
        enabled = true
        per_page = ["json", "llm_txt"]
        site_wide = ["index_json", "llm_full"]
    """
    
    def __init__(self, site: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize output formats generator.
        
        Args:
            site: Site instance
            config: Configuration dict from bengal.toml
        """
        self.site = site
        self.config = self._normalize_config(config or {})
    
    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize configuration to support both simple and advanced formats.
        
        Simple format (from [build.output_formats]):
            {
                'enabled': True,
                'json': True,
                'llm_txt': True,
                'site_json': True,
                'site_llm': True
            }
        
        Advanced format (from [output_formats]):
            {
                'enabled': True,
                'per_page': ['json', 'llm_txt'],
                'site_wide': ['index_json', 'llm_full'],
                'options': {...}
            }
        
        Args:
            config: Raw configuration from bengal.toml
            
        Returns:
            Normalized configuration in advanced format
        """
        # Start with defaults
        normalized = self._default_config()
        
        # If config is empty or disabled, return defaults
        if not config:
            return normalized
        
        # Check if it's the advanced format (has per_page or site_wide keys)
        is_advanced = 'per_page' in config or 'site_wide' in config
        
        if is_advanced:
            # Advanced format - merge with defaults
            normalized.update(config)
        else:
            # Simple format - convert to advanced format
            per_page = []
            site_wide = []
            
            # Map simple format keys to advanced format
            if config.get('json', False):
                per_page.append('json')
            if config.get('llm_txt', False):
                per_page.append('llm_txt')
            if config.get('site_json', False):
                site_wide.append('index_json')
            if config.get('site_llm', False):
                site_wide.append('llm_full')
            
            # Update normalized config
            normalized['per_page'] = per_page if per_page else normalized['per_page']
            normalized['site_wide'] = site_wide if site_wide else normalized['site_wide']
            
            # Copy enabled flag if present
            if 'enabled' in config:
                normalized['enabled'] = config['enabled']
            
            # Copy options if present
            if 'options' in config:
                normalized['options'].update(config['options'])
        
        return normalized
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'enabled': True,
            'per_page': ['json', 'llm_txt'],  # JSON + LLM text by default (AI-native!)
            'site_wide': ['index_json', 'llm_full'],  # Search index + full LLM text
            'options': {
                'include_html_content': True,
                'include_plain_text': True,
                'excerpt_length': 200,
                'exclude_sections': [],
                'exclude_patterns': ['404.html', 'search.html'],
                'json_indent': None,  # None = compact, 2 = pretty
                'llm_separator_width': 80,
            }
        }
    
    def generate(self) -> None:
        """
        Generate all enabled output formats.
        
        Checks configuration to determine which formats to generate,
        filters pages based on exclusion rules, then generates:
        1. Per-page formats (JSON, LLM text)
        2. Site-wide formats (index.json, llm-full.txt)
        
        All file writes are atomic to prevent corruption during builds.
        """
        if not self.config.get('enabled', True):
            logger.debug("output_formats_disabled")
            return
        
        per_page = self.config.get('per_page', ['json'])
        site_wide = self.config.get('site_wide', ['index_json'])
        
        logger.debug(
            "generating_output_formats",
            per_page_formats=per_page,
            site_wide_formats=site_wide
        )
        
        # Filter pages based on exclusions
        pages = self._filter_pages()
        
        # Track what we generated
        generated = []
        
        # Per-page outputs
        if 'json' in per_page:
            count = self._generate_page_json(pages)
            generated.append(f"JSON ({count} files)")
            logger.debug("generated_page_json", file_count=count)
        
        if 'llm_txt' in per_page:
            count = self._generate_page_txt(pages)
            generated.append(f"LLM text ({count} files)")
            logger.debug("generated_page_txt", file_count=count)
        
        # Site-wide outputs
        if 'index_json' in site_wide:
            self._generate_site_index_json(pages)
            generated.append("index.json")
            logger.debug("generated_site_index_json")
        
        if 'llm_full' in site_wide:
            self._generate_site_llm_txt(pages)
            generated.append("llm-full.txt")
            logger.debug("generated_site_llm_full")
        
        if generated:
            logger.info(
                "output_formats_complete",
                formats=generated
            )
    
    def _filter_pages(self) -> List[Any]:
        """
        Filter pages based on exclusion rules.
        
        Excludes pages that:
        - Have no output path (not rendered yet)
        - Are in excluded sections
        - Match excluded patterns (e.g., '404.html', 'search.html')
        
        Returns:
            List of pages to include in output formats
        """
        options = self.config.get('options', {})
        exclude_sections = options.get('exclude_sections', [])
        exclude_patterns = options.get('exclude_patterns', ['404.html', 'search.html'])
        
        logger.debug(
            "filtering_pages_for_output",
            total_pages=len(self.site.pages),
            exclude_sections=exclude_sections,
            exclude_patterns=exclude_patterns
        )
        
        filtered = []
        excluded_by_section = 0
        excluded_by_pattern = 0
        excluded_no_output = 0
        
        for page in self.site.pages:
            # Skip if no output path
            if not page.output_path:
                excluded_no_output += 1
                continue
            
            # Check section exclusions
            section_name = getattr(page._section, 'name', '') if hasattr(page, '_section') and page._section else ''
            if section_name in exclude_sections:
                excluded_by_section += 1
                continue
            
            # Check pattern exclusions
            output_str = str(page.output_path)
            if any(pattern in output_str for pattern in exclude_patterns):
                excluded_by_pattern += 1
                continue
            
            filtered.append(page)
        
        logger.debug(
            "page_filtering_complete",
            filtered_pages=len(filtered),
            excluded_no_output=excluded_no_output,
            excluded_by_section=excluded_by_section,
            excluded_by_pattern=excluded_by_pattern
        )
        
        return filtered
    
    def _generate_page_json(self, pages: List[Any]) -> int:
        """
        Generate JSON file for each page.
        
        Args:
            pages: List of pages to process
            
        Returns:
            Number of JSON files generated
        """
        options = self.config.get('options', {})
        indent = options.get('json_indent')
        include_html = options.get('include_html_content', True)
        include_text = options.get('include_plain_text', True)
        excerpt_length = options.get('excerpt_length', 200)
        
        count = 0
        for page in pages:
            # Build JSON data
            data = self._page_to_json(
                page,
                include_html=include_html,
                include_text=include_text,
                excerpt_length=excerpt_length
            )
            
            # Determine output path (next to HTML file)
            json_path = self._get_page_json_path(page)
            if not json_path:
                continue
            
            # Ensure directory exists
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON atomically (crash-safe)
            from bengal.utils.atomic_write import AtomicFile
            with AtomicFile(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            count += 1
        
        return count
    
    def _generate_page_txt(self, pages: List[Any]) -> int:
        """
        Generate LLM-friendly text file for each page.
        
        Args:
            pages: List of pages to process
            
        Returns:
            Number of text files generated
        """
        options = self.config.get('options', {})
        separator_width = options.get('llm_separator_width', 80)
        
        count = 0
        for page in pages:
            # Build text content
            text = self._page_to_llm_text(page, separator_width)
            
            # Determine output path (next to HTML file)
            txt_path = self._get_page_txt_path(page)
            if not txt_path:
                continue
            
            # Ensure directory exists
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write text atomically (crash-safe)
            from bengal.utils.atomic_write import AtomicFile
            with AtomicFile(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            count += 1
        
        return count
    
    def _generate_site_index_json(self, pages: List[Any]) -> None:
        """
        Generate site-wide index.json with all pages.
        
        Creates a comprehensive JSON index suitable for client-side search.
        Includes page summaries, sections, and tags with counts.
        
        Args:
            pages: List of pages to include
        
        Output Format:
            {
              "site": {"title": "...", "baseurl": "...", ...},
              "pages": [{...}, {...}],  // Array of page summaries
              "sections": [{...}],       // Section counts
              "tags": [{...}]            // Tag counts sorted by popularity
            }
        """
        logger.debug(
            "generating_site_index_json",
            page_count=len(pages)
        )
        
        options = self.config.get('options', {})
        indent = options.get('json_indent')
        excerpt_length = options.get('excerpt_length', 200)
        
        # Build site metadata
        site_data = {
            'site': {
                'title': self.site.config.get('title', 'Bengal Site'),
                'description': self.site.config.get('description', ''),
                'baseurl': self.site.config.get('baseurl', ''),
                'build_time': datetime.now().isoformat()
            },
            'pages': [],
            'sections': {},
            'tags': {}
        }
        
        # Add each page (summary only, no full content)
        for page in pages:
            page_summary = self._page_to_summary(page, excerpt_length)
            site_data['pages'].append(page_summary)
            
            # Count sections
            section = page_summary.get('section', '')
            if section:
                site_data['sections'][section] = site_data['sections'].get(section, 0) + 1
            
            # Count tags
            for tag in page_summary.get('tags', []):
                site_data['tags'][tag] = site_data['tags'].get(tag, 0) + 1
        
        # Convert counts to lists
        site_data['sections'] = [
            {'name': name, 'count': count}
            for name, count in sorted(site_data['sections'].items())
        ]
        site_data['tags'] = [
            {'name': name, 'count': count}
            for name, count in sorted(site_data['tags'].items(), key=lambda x: -x[1])
        ]
        
        logger.debug(
            "site_index_data_aggregated",
            total_pages=len(site_data['pages']),
            sections=len(site_data['sections']),
            tags=len(site_data['tags'])
        )
        
        # Write to root of output directory atomically (crash-safe)
        from bengal.utils.atomic_write import AtomicFile
        index_path = self.site.output_dir / 'index.json'
        with AtomicFile(index_path, 'w', encoding='utf-8') as f:
            json.dump(site_data, f, indent=indent, ensure_ascii=False)
        
        logger.debug(
            "site_index_json_written",
            path=str(index_path),
            size_kb=index_path.stat().st_size / 1024
        )
    
    def _generate_site_llm_txt(self, pages: List[Any]) -> None:
        """
        Generate site-wide llm-full.txt with all pages.
        
        Creates a single text file containing all site content in an
        AI/LLM-friendly format. Each page is separated by a clear divider
        and includes metadata (URL, section, tags, date) followed by content.
        
        Args:
            pages: List of pages to include
        
        Use Cases:
            - AI assistant training/context
            - Full-text search indexing
            - Content analysis and extraction
        """
        options = self.config.get('options', {})
        separator_width = options.get('llm_separator_width', 80)
        separator = '=' * separator_width
        
        lines = []
        
        # Site header
        title = self.site.config.get('title', 'Bengal Site')
        baseurl = self.site.config.get('baseurl', '')
        lines.append(f"# {title}\n")
        if baseurl:
            lines.append(f"Site: {baseurl}")
        lines.append(f"Build Date: {datetime.now().isoformat()}")
        lines.append(f"Total Pages: {len(pages)}\n")
        lines.append(separator + "\n")
        
        # Add each page
        for idx, page in enumerate(pages, 1):
            lines.append(f"\n## Page {idx}/{len(pages)}: {page.title}\n")
            
            # Page metadata
            url = self._get_page_url(page)
            lines.append(f"URL: {url}")
            
            section_name = getattr(page._section, 'name', '') if hasattr(page, '_section') and page._section else ''
            if section_name:
                lines.append(f"Section: {section_name}")
            
            if page.tags:
                lines.append(f"Tags: {', '.join(page.tags)}")
            
            if page.date:
                lines.append(f"Date: {page.date.strftime('%Y-%m-%d')}")
            
            lines.append("")  # Blank line before content
            
            # Page content (plain text)
            content = self._strip_html(page.parsed_ast or page.content)
            lines.append(content)
            
            lines.append("\n" + separator + "\n")
        
        # Write to root of output directory atomically (crash-safe)
        from bengal.utils.atomic_write import AtomicFile
        llm_path = self.site.output_dir / 'llm-full.txt'
        with AtomicFile(llm_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _page_to_json(self, page: Any, include_html: bool = True,
                     include_text: bool = True, excerpt_length: int = 200) -> Dict[str, Any]:
        """
        Convert page to JSON representation.
        
        Args:
            page: Page object
            include_html: Include full HTML content
            include_text: Include plain text content
            excerpt_length: Length of excerpt
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        data = {
            'url': self._get_page_url(page),
            'title': page.title,
            'description': page.metadata.get('description', ''),
        }
        
        # Date
        if page.date:
            data['date'] = page.date.isoformat()
        
        # Content
        if include_html and page.parsed_ast:
            data['content'] = page.parsed_ast
        
        # Plain text
        content_text = self._strip_html(page.parsed_ast or page.content)
        if include_text:
            data['plain_text'] = content_text
        
        # Excerpt
        data['excerpt'] = self._generate_excerpt(content_text, excerpt_length)
        
        # Metadata (serialize dates and other non-JSON types)
        data['metadata'] = {}
        skipped_keys = []
        for k, v in page.metadata.items():
            if k in ['content', 'parsed_ast', 'rendered_html', '_generated']:
                continue
            # Only include JSON-serializable values
            try:
                # Convert dates to ISO format strings
                if isinstance(v, datetime):
                    data['metadata'][k] = v.isoformat()
                elif hasattr(v, 'isoformat'):  # datetime.date
                    data['metadata'][k] = v.isoformat()
                # Test if value is JSON serializable
                elif isinstance(v, (str, int, float, bool, type(None))):
                    data['metadata'][k] = v
                elif isinstance(v, (list, dict)):
                    # Try to serialize, skip if it fails
                    json.dumps(v)
                    data['metadata'][k] = v
                # Skip complex objects that can't be serialized
            except (TypeError, ValueError) as e:
                # Skip non-serializable values
                skipped_keys.append(k)
                logger.debug(
                    "json_serialization_skipped",
                    page=str(page.source_path),
                    key=k,
                    value_type=type(v).__name__,
                    reason=str(e)[:100]
                )
        
        if skipped_keys:
            logger.debug(
                "metadata_keys_skipped",
                page=str(page.source_path),
                skipped_count=len(skipped_keys),
                keys=skipped_keys
            )
        
        # Section
        if hasattr(page, '_section') and page._section:
            data['section'] = getattr(page._section, 'name', '')
        
        # Tags
        if page.tags:
            data['tags'] = page.tags
        
        # Stats
        word_count = len(content_text.split())
        data['word_count'] = word_count
        data['reading_time'] = max(1, round(word_count / 200))  # 200 wpm
        
        return data
    
    def _page_to_summary(self, page: Any, excerpt_length: int = 200) -> Dict[str, Any]:
        """
        Convert page to summary for site index.
        
        Creates a search-optimized page summary with enhanced metadata.
        Includes standard fields (title, URL, excerpt) plus searchable
        metadata like tags, categories, content type, etc.
        
        Args:
            page: Page object
            excerpt_length: Length of excerpt in characters
            
        Returns:
            Dictionary with page summary including:
            - objectID: Unique identifier for search
            - url: Absolute URL with baseurl
            - title, description, excerpt: Display text
            - tags, section, category: Taxonomy
            - word_count, reading_time: Stats
            - Plus any custom frontmatter fields
        """
        content_text = self._strip_html(page.parsed_ast or page.content)
        
        # Get relative URI (path without domain)
        page_uri = self._get_page_url(page)
        
        # Get baseurl from site config and construct absolute URL
        baseurl = self.site.config.get('baseurl', '').rstrip('/')
        page_url = f"{baseurl}{page_uri}" if baseurl else page_uri
        
        summary = {
            'objectID': page_uri,  # Unique identifier (relative path)
            'url': page_url,       # Absolute URL with baseurl
            'uri': page_uri,       # Relative path (Hugo convention)
            'title': page.title,
            'description': page.metadata.get('description', ''),
            'excerpt': self._generate_excerpt(content_text, excerpt_length),
        }
        
        # Optional fields
        if page.date:
            summary['date'] = page.date.strftime('%Y-%m-%d')
        
        if hasattr(page, '_section') and page._section:
            summary['section'] = getattr(page._section, 'name', '')
        
        if page.tags:
            summary['tags'] = page.tags
        
        # Stats
        word_count = len(content_text.split())
        summary['word_count'] = word_count
        summary['reading_time'] = max(1, round(word_count / 200))
        
        # Enhanced metadata for search (from standardized frontmatter)
        metadata = page.metadata
        
        # Content type and layout
        if metadata.get('type'):
            summary['type'] = metadata['type']
        if metadata.get('layout'):
            summary['layout'] = metadata['layout']
        
        # Authorship
        if metadata.get('author'):
            summary['author'] = metadata['author']
        if metadata.get('authors'):
            summary['authors'] = metadata['authors']
        
        # Categories and taxonomy
        if metadata.get('category'):
            summary['category'] = metadata['category']
        if metadata.get('categories'):
            summary['categories'] = metadata['categories']
        
        # Weight/order for sorting
        if metadata.get('weight') is not None:
            summary['weight'] = metadata['weight']
        
        # Status flags
        if metadata.get('draft'):
            summary['draft'] = True
        if metadata.get('featured'):
            summary['featured'] = True
        
        # Search-specific fields
        if metadata.get('search_keywords'):
            summary['search_keywords'] = metadata['search_keywords']
        if metadata.get('search_exclude'):
            summary['search_exclude'] = True
        
        # API/CLI specific
        if metadata.get('cli_name'):
            summary['cli_name'] = metadata['cli_name']
        if metadata.get('api_module'):
            summary['api_module'] = metadata['api_module']
        
        # Difficulty/level for tutorials
        if metadata.get('difficulty'):
            summary['difficulty'] = metadata['difficulty']
        if metadata.get('level'):
            summary['level'] = metadata['level']
        
        # Related content
        if metadata.get('related'):
            summary['related'] = metadata['related']
        
        # Last modified (if different from date)
        if metadata.get('lastmod'):
            lastmod = metadata['lastmod']
            # Convert date objects to ISO format string
            if hasattr(lastmod, 'isoformat'):
                summary['lastmod'] = lastmod.isoformat() if hasattr(lastmod, 'isoformat') else str(lastmod)
            else:
                summary['lastmod'] = str(lastmod)
        
        # Content text for full-text search
        # Check config option for full content vs excerpt
        options = self.config.get('options', {})
        include_full_content = options.get('include_full_content_in_index', False)
        
        if len(content_text) > 0:
            if include_full_content:
                # Include full content for comprehensive search
                summary['content'] = content_text
            else:
                # Include extended excerpt (3x normal length)
                summary['content'] = self._generate_excerpt(content_text, excerpt_length * 3)
        
        # Add source file path if available (useful for docs)
        if metadata.get('source_file'):
            summary['source_file'] = metadata['source_file']
        
        # Add directory/path structure for hierarchical navigation
        if page.url:
            # Extract directory path (everything except filename)
            path_parts = page.url.strip('/').split('/')
            if len(path_parts) > 1:
                summary['dir'] = '/' + '/'.join(path_parts[:-1]) + '/'
            else:
                summary['dir'] = '/'
        
        # Add kind/content type for filtering (alternative naming)
        if result_type := summary.get('type'):
            summary['kind'] = result_type  # Alias for Hugo compatibility
        
        return summary
    
    def _page_to_llm_text(self, page: Any, separator_width: int = 80) -> str:
        """
        Convert page to LLM-friendly text format.
        
        Args:
            page: Page object
            separator_width: Width of separator line
            
        Returns:
            Formatted text string
        """
        lines = []
        
        # Title
        lines.append(f"# {page.title}\n")
        
        # Metadata
        url = self._get_page_url(page)
        lines.append(f"URL: {url}")
        
        section_name = getattr(page._section, 'name', '') if hasattr(page, '_section') and page._section else ''
        if section_name:
            lines.append(f"Section: {section_name}")
        
        if page.tags:
            lines.append(f"Tags: {', '.join(page.tags)}")
        
        if page.date:
            lines.append(f"Date: {page.date.strftime('%Y-%m-%d')}")
        
        lines.append("\n" + ("-" * separator_width) + "\n")
        
        # Content (plain text)
        content = self._strip_html(page.parsed_ast or page.content)
        lines.append(content)
        
        # Footer metadata
        word_count = len(content.split())
        reading_time = max(1, round(word_count / 200))
        
        lines.append("\n" + ("-" * separator_width))
        lines.append("\nMetadata:")
        if 'author' in page.metadata:
            lines.append(f"- Author: {page.metadata['author']}")
        lines.append(f"- Word Count: {word_count}")
        lines.append(f"- Reading Time: {reading_time} minutes")
        
        return '\n'.join(lines)
    
    def _get_page_url(self, page: Any) -> str:
        """
        Get clean URL for page.
        
        Args:
            page: Page object
            
        Returns:
            URL string (relative to baseurl)
        """
        if not page.output_path:
            return f"/{getattr(page, 'slug', page.source_path.stem)}/"
        
        try:
            rel_path = page.output_path.relative_to(self.site.output_dir)
            url = f"/{rel_path}".replace('\\', '/')
            # Clean up /index.html
            url = url.replace('/index.html', '/')
            return url
        except ValueError:
            return f"/{getattr(page, 'slug', page.source_path.stem)}/"
    
    def _get_page_json_path(self, page: Any) -> Optional[Path]:
        """
        Get path for page's JSON file.
        
        Args:
            page: Page object
            
        Returns:
            Path object or None
        """
        if not page.output_path:
            return None
        
        # If output is index.html, put index.json next to it
        if page.output_path.name == 'index.html':
            return page.output_path.parent / 'index.json'
        
        # If output is page.html, put page.json next to it
        return page.output_path.with_suffix('.json')
    
    def _get_page_txt_path(self, page: Any) -> Optional[Path]:
        """
        Get path for page's text file.
        
        Args:
            page: Page object
            
        Returns:
            Path object or None
        """
        if not page.output_path:
            return None
        
        # If output is index.html, put index.txt next to it
        if page.output_path.name == 'index.html':
            return page.output_path.parent / 'index.txt'
        
        # If output is page.html, put page.txt next to it
        return page.output_path.with_suffix('.txt')
    
    def _strip_html(self, text: str) -> str:
        """
        Remove HTML tags from text.
        
        Args:
            text: HTML text
            
        Returns:
            Plain text
        """
        if not text:
            return ''
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        try:
            import html
            text = html.unescape(text)
        except ImportError:
            pass
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _generate_excerpt(self, text: str, length: int = 200) -> str:
        """
        Generate excerpt from text.
        
        Args:
            text: Source text
            length: Maximum length
            
        Returns:
            Excerpt string
        """
        if not text:
            return ''
        
        if len(text) <= length:
            return text
        
        # Find last space before limit
        excerpt = text[:length].rsplit(' ', 1)[0]
        return excerpt + "..."

