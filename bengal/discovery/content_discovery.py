"""
Content discovery - finds and organizes pages and sections.
"""

from pathlib import Path
from typing import List, Tuple
import frontmatter

from bengal.core.page import Page
from bengal.core.section import Section
from bengal.utils.logger import get_logger


class ContentDiscovery:
    """
    Discovers and organizes content files into pages and sections.
    """
    
    def __init__(self, content_dir: Path) -> None:
        """
        Initialize content discovery.
        
        Args:
            content_dir: Root content directory
        """
        self.content_dir = content_dir
        self.sections: List[Section] = []
        self.pages: List[Page] = []
        self.logger = get_logger(__name__)
    
    def discover(self) -> Tuple[List[Section], List[Page]]:
        """
        Discover all content in the content directory.
        
        Returns:
            Tuple of (sections, pages)
        """
        self.logger.info("content_discovery_start", content_dir=str(self.content_dir))
        
        if not self.content_dir.exists():
            self.logger.warning("content_dir_missing",
                              content_dir=str(self.content_dir),
                              action="returning_empty")
            return self.sections, self.pages
        
        # Walk top-level items directly (no root section wrapper)
        for item in sorted(self.content_dir.iterdir()):
            # Skip hidden files and directories
            if item.name.startswith(('.', '_')) and item.name not in ('_index.md', '_index.markdown'):
                continue
            
            if item.is_file() and self._is_content_file(item):
                # Top-level page (no section)
                page = self._create_page(item)
                self.pages.append(page)
            
            elif item.is_dir():
                # Top-level section
                section = Section(
                    name=item.name,
                    path=item,
                )
                
                # Recursively walk the subdirectory
                self._walk_directory(item, section)
                
                # Only add section if it has content
                if section.pages or section.subsections:
                    self.sections.append(section)
        
        # Calculate metrics
        top_level_sections = len([s for s in self.sections if not hasattr(s, 'parent') or s.parent is None])
        top_level_pages = len([p for p in self.pages if not any(p in s.pages for s in self.sections)])
        
        self.logger.info("content_discovery_complete",
                        total_sections=len(self.sections),
                        total_pages=len(self.pages),
                        top_level_sections=top_level_sections,
                        top_level_pages=top_level_pages)
        
        return self.sections, self.pages
    
    def _walk_directory(self, directory: Path, parent_section: Section) -> None:
        """
        Recursively walk a directory to discover content.
        
        Args:
            directory: Directory to walk
            parent_section: Parent section to add content to
        """
        if not directory.exists():
            return
        
        # Iterate through items in directory (non-recursively for control)
        for item in sorted(directory.iterdir()):
            # Skip hidden files and directories
            if item.name.startswith(('.', '_')) and item.name not in ('_index.md', '_index.markdown'):
                continue
            
            if item.is_file() and self._is_content_file(item):
                # Create a page
                page = self._create_page(item)
                parent_section.add_page(page)
                self.pages.append(page)
            
            elif item.is_dir():
                # Create a subsection
                section = Section(
                    name=item.name,
                    path=item,
                )
                
                # Recursively walk the subdirectory
                self._walk_directory(item, section)
                
                # Only add section if it has content
                if section.pages or section.subsections:
                    parent_section.add_subsection(section)
                    self.sections.append(section)
    
    def _is_content_file(self, file_path: Path) -> bool:
        """
        Check if a file is a content file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if it's a content file
        """
        content_extensions = {'.md', '.markdown', '.rst', '.txt'}
        return file_path.suffix.lower() in content_extensions
    
    def _create_page(self, file_path: Path) -> Page:
        """
        Create a Page object from a file with robust error handling.
        
        Handles:
        - Valid frontmatter
        - Invalid YAML in frontmatter  
        - Missing frontmatter
        - File encoding issues
        - IO errors
        
        Args:
            file_path: Path to content file
            
        Returns:
            Page object (always succeeds with fallback metadata)
            
        Raises:
            IOError: Only if file cannot be read at all
        """
        try:
            content, metadata = self._parse_content_file(file_path)
            
            page = Page(
                source_path=file_path,
                content=content,
                metadata=metadata,
            )
            
            self.logger.debug("page_created",
                            page_path=str(file_path),
                            has_metadata=bool(metadata),
                            has_parse_error='_parse_error' in metadata)
            
            return page
        except Exception as e:
            self.logger.error("page_creation_failed",
                            file_path=str(file_path),
                            error=str(e),
                            error_type=type(e).__name__)
            raise
    
    def _parse_content_file(self, file_path: Path) -> tuple:
        """
        Parse content file with robust error handling.
        
        Args:
            file_path: Path to content file
            
        Returns:
            Tuple of (content, metadata)
            
        Raises:
            IOError: If file cannot be read
        """
        import yaml
        
        # Read file once
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except UnicodeDecodeError as e:
            # Try different encodings
            self.logger.warning("encoding_decode_failed",
                              file_path=str(file_path),
                              encoding="utf-8",
                              fallback="latin-1")
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    file_content = f.read()
            except Exception:
                # Give up
                self.logger.error("file_decode_failed",
                                file_path=str(file_path),
                                error=str(e),
                                tried_encodings=["utf-8", "latin-1"])
                raise IOError(f"Cannot decode {file_path}: {e}") from e
        except IOError as e:
            self.logger.error("file_read_failed",
                            file_path=str(file_path),
                            error=str(e),
                            error_type=type(e).__name__)
            raise
        
        # Parse frontmatter
        try:
            post = frontmatter.loads(file_content)
            content = post.content
            metadata = dict(post.metadata)
            return content, metadata
            
        except yaml.YAMLError as e:
            # YAML syntax error in frontmatter
            self.logger.warning("frontmatter_parse_failed",
                              file_path=str(file_path),
                              error=str(e),
                              error_type="yaml_syntax",
                              action="processing_without_metadata",
                              suggestion="Fix frontmatter YAML syntax")
            
            # Try to extract content (skip broken frontmatter)
            content = self._extract_content_skip_frontmatter(file_content)
            
            # Create minimal metadata for identification
            metadata = {
                '_parse_error': str(e),
                '_parse_error_type': 'yaml',
                '_source_file': str(file_path),
                'title': file_path.stem.replace('-', ' ').replace('_', ' ').title()
            }
            
            return content, metadata
        
        except Exception as e:
            # Unexpected error
            self.logger.warning("content_parse_unexpected_error",
                              file_path=str(file_path),
                              error=str(e),
                              error_type=type(e).__name__,
                              action="using_full_file_as_content")
            
            # Use entire file as content
            metadata = {
                '_parse_error': str(e),
                '_parse_error_type': 'unknown',
                '_source_file': str(file_path),
                'title': file_path.stem.replace('-', ' ').replace('_', ' ').title()
            }
            
            return file_content, metadata
    
    def _extract_content_skip_frontmatter(self, file_content: str) -> str:
        """
        Extract content, skipping broken frontmatter section.
        
        Frontmatter is between --- delimiters at start of file.
        If parsing failed, skip the section entirely.
        
        Args:
            file_content: Full file content
            
        Returns:
            Content without frontmatter section
        """
        # Split on --- delimiters
        parts = file_content.split('---', 2)
        
        if len(parts) >= 3:
            # Format: --- frontmatter --- content
            # Return content (3rd part)
            return parts[2].strip()
        elif len(parts) == 2:
            # Format: --- frontmatter (no closing delimiter)
            # Return second part
            return parts[1].strip()
        else:
            # No frontmatter delimiters, return whole file
            return file_content.strip()

