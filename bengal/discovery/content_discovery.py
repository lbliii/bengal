"""
Content discovery - finds and organizes pages and sections.
"""

from pathlib import Path
from typing import List, Tuple
import frontmatter

from bengal.core.page import Page
from bengal.core.section import Section


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
    
    def discover(self) -> Tuple[List[Section], List[Page]]:
        """
        Discover all content in the content directory.
        
        Returns:
            Tuple of (sections, pages)
        """
        # Create root section
        root_section = Section(
            name="root",
            path=self.content_dir,
        )
        
        # Walk the content directory
        self._walk_directory(self.content_dir, root_section)
        
        # Only add root section if it has content
        if root_section.pages or root_section.subsections:
            self.sections.append(root_section)
        
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
        Create a Page object from a file.
        
        Args:
            file_path: Path to content file
            
        Returns:
            Page object
        """
        # Parse frontmatter and content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                content = post.content
                metadata = dict(post.metadata)
        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}")
            # Fallback to reading as plain text
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                metadata = {}
        
        page = Page(
            source_path=file_path,
            content=content,
            metadata=metadata,
        )
        
        return page

