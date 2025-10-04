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


class OutputFormatsGenerator:
    """
    Generates custom output formats for pages.
    
    Supports:
    - Per-page JSON output (page.json next to page.html)
    - Per-page LLM text output (page.txt next to page.html)
    - Site-wide index.json (searchable index of all pages)
    - Site-wide llm-full.txt (full site content for AI)
    """
    
    def __init__(self, site: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize output formats generator.
        
        Args:
            site: Site instance
            config: Configuration dict from bengal.toml
        """
        self.site = site
        self.config = config or self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'enabled': True,
            'per_page': ['json'],  # JSON by default, LLM text opt-in
            'site_wide': ['index_json'],  # Index by default, llm-full opt-in
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
        """Generate all enabled output formats."""
        if not self.config.get('enabled', True):
            return
        
        per_page = self.config.get('per_page', ['json'])
        site_wide = self.config.get('site_wide', ['index_json'])
        
        # Filter pages based on exclusions
        pages = self._filter_pages()
        
        # Track what we generated
        generated = []
        
        # Per-page outputs
        if 'json' in per_page:
            count = self._generate_page_json(pages)
            generated.append(f"JSON ({count} files)")
        
        if 'llm_txt' in per_page:
            count = self._generate_page_txt(pages)
            generated.append(f"LLM text ({count} files)")
        
        # Site-wide outputs
        if 'index_json' in site_wide:
            self._generate_site_index_json(pages)
            generated.append("index.json")
        
        if 'llm_full' in site_wide:
            self._generate_site_llm_txt(pages)
            generated.append("llm-full.txt")
        
        if generated:
            print(f"   ├─ Output formats: {', '.join(generated)} ✓")
    
    def _filter_pages(self) -> List[Any]:
        """Filter pages based on exclusion rules."""
        options = self.config.get('options', {})
        exclude_sections = options.get('exclude_sections', [])
        exclude_patterns = options.get('exclude_patterns', ['404.html', 'search.html'])
        
        filtered = []
        for page in self.site.pages:
            # Skip if no output path
            if not page.output_path:
                continue
            
            # Check section exclusions
            section_name = getattr(page._section, 'name', '') if hasattr(page, '_section') and page._section else ''
            if section_name in exclude_sections:
                continue
            
            # Check pattern exclusions
            output_str = str(page.output_path)
            if any(pattern in output_str for pattern in exclude_patterns):
                continue
            
            filtered.append(page)
        
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
            
            # Write JSON
            with open(json_path, 'w', encoding='utf-8') as f:
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
            
            # Write text
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            count += 1
        
        return count
    
    def _generate_site_index_json(self, pages: List[Any]) -> None:
        """
        Generate site-wide index.json with all pages.
        
        Args:
            pages: List of pages to include
        """
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
        
        # Write to root of output directory
        index_path = self.site.output_dir / 'index.json'
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(site_data, f, indent=indent, ensure_ascii=False)
    
    def _generate_site_llm_txt(self, pages: List[Any]) -> None:
        """
        Generate site-wide llm-full.txt with all pages.
        
        Args:
            pages: List of pages to include
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
        
        # Write to root of output directory
        llm_path = self.site.output_dir / 'llm-full.txt'
        with open(llm_path, 'w', encoding='utf-8') as f:
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
            except (TypeError, ValueError):
                # Skip non-serializable values
                pass
        
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
        Convert page to summary (for site index).
        
        Args:
            page: Page object
            excerpt_length: Length of excerpt
            
        Returns:
            Dictionary with page summary
        """
        content_text = self._strip_html(page.parsed_ast or page.content)
        
        summary = {
            'url': self._get_page_url(page),
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

