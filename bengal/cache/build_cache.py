"""
Build Cache - Tracks file changes and dependencies for incremental builds.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedContentCache:
    """
    Cached parsed markdown content for a page.
    
    This allows skipping markdown parsing when only templates change.
    Optimization #2: Saves 20-30% time on template changes.
    """
    html: str                     # Rendered HTML (post-markdown, pre-template)
    toc: str                      # Table of contents HTML
    toc_items: list[dict[str, Any]]  # Structured TOC data
    metadata_hash: str            # SHA256 of frontmatter (detect metadata changes)
    template: str                 # Template name used
    parser_version: str           # Parser version (e.g., "mistune-3.0")
    timestamp: str                # When cached (ISO format)
    size_bytes: int               # Size for cache management


@dataclass
class BuildCache:
    """
    Tracks file hashes and dependencies between builds.
    
    IMPORTANT PERSISTENCE CONTRACT:
    - This cache must NEVER contain object references (Page, Section, Asset objects)
    - All data must be JSON-serializable (paths, strings, numbers, lists, dicts, sets)
    - Object relationships are rebuilt each build from cached paths
    
    Attributes:
        file_hashes: Mapping of file paths to their SHA256 hashes
        dependencies: Mapping of pages to their dependencies (templates, partials, etc.)
        output_sources: Mapping of output files to their source files
        taxonomy_deps: Mapping of taxonomy terms to affected pages
        page_tags: Mapping of page paths to their tags (for detecting tag changes)
        tag_to_pages: Inverted index mapping tag slug to page paths (for O(1) reconstruction)
        known_tags: Set of all tag slugs from previous build (for detecting deletions)
        parsed_content: Cached parsed HTML/TOC (Optimization #2)
        last_build: Timestamp of last successful build
    """
    
    file_hashes: dict[str, str] = field(default_factory=dict)
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    output_sources: dict[str, str] = field(default_factory=dict)
    taxonomy_deps: dict[str, set[str]] = field(default_factory=dict)
    page_tags: dict[str, set[str]] = field(default_factory=dict)
    
    # Inverted index for fast taxonomy reconstruction (NEW)
    tag_to_pages: dict[str, set[str]] = field(default_factory=dict)
    known_tags: set[str] = field(default_factory=set)
    
    parsed_content: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_build: str | None = None
    
    def __post_init__(self) -> None:
        """Convert sets from lists after JSON deserialization."""
        # Convert dependency lists back to sets
        self.dependencies = {
            k: set(v) if isinstance(v, list) else v
            for k, v in self.dependencies.items()
        }
        # Convert taxonomy dependency lists back to sets
        self.taxonomy_deps = {
            k: set(v) if isinstance(v, list) else v
            for k, v in self.taxonomy_deps.items()
        }
        # Convert page tags lists back to sets
        self.page_tags = {
            k: set(v) if isinstance(v, list) else v
            for k, v in self.page_tags.items()
        }
        # Convert tag_to_pages lists back to sets
        self.tag_to_pages = {
            k: set(v) if isinstance(v, list) else v
            for k, v in self.tag_to_pages.items()
        }
        # Convert known_tags list back to set
        if isinstance(self.known_tags, list):
            self.known_tags = set(self.known_tags)
        # Parsed content is already in dict format (no conversion needed)
    
    @classmethod
    def load(cls, cache_path: Path) -> 'BuildCache':
        """
        Load build cache from disk.
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            BuildCache instance (empty if file doesn't exist or is invalid)
        """
        if not cache_path.exists():
            return cls()
        
        try:
            with open(cache_path, encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert lists back to sets in dependencies
            if 'dependencies' in data:
                data['dependencies'] = {
                    k: set(v) for k, v in data['dependencies'].items()
                }
            
            # Convert lists back to sets in tag_to_pages
            if 'tag_to_pages' in data:
                data['tag_to_pages'] = {
                    k: set(v) for k, v in data['tag_to_pages'].items()
                }
            
            # Convert list back to set in known_tags
            if 'known_tags' in data and isinstance(data['known_tags'], list):
                data['known_tags'] = set(data['known_tags'])
            
            if 'taxonomy_deps' in data:
                data['taxonomy_deps'] = {
                    k: set(v) for k, v in data['taxonomy_deps'].items()
                }
            
            if 'page_tags' in data:
                data['page_tags'] = {
                    k: set(v) for k, v in data['page_tags'].items()
                }
            
            return cls(**data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("cache_load_failed",
                          cache_path=str(cache_path),
                          error=str(e),
                          error_type=type(e).__name__,
                          action="using_fresh_cache")
            return cls()
    
    def save(self, cache_path: Path) -> None:
        """
        Save build cache to disk.
        
        Args:
            cache_path: Path to cache file
        
        Raises:
            IOError: If cache file cannot be written
            json.JSONEncodeError: If cache data cannot be serialized
        """
        # Ensure parent directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert sets to lists for JSON serialization
        data = {
            'file_hashes': self.file_hashes,
            'dependencies': {k: list(v) for k, v in self.dependencies.items()},
            'output_sources': self.output_sources,
            'taxonomy_deps': {k: list(v) for k, v in self.taxonomy_deps.items()},
            'page_tags': {k: list(v) for k, v in self.page_tags.items()},
            'parsed_content': self.parsed_content,  # NEW: Already in dict format
            'last_build': datetime.now().isoformat()
        }
        
        try:
            # Write cache atomically (crash-safe)
            from bengal.utils.atomic_write import AtomicFile
            with AtomicFile(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("cache_saved",
                        cache_path=str(cache_path),
                        tracked_files=len(self.file_hashes),
                        dependencies=len(self.dependencies),
                        cached_content=len(self.parsed_content))
        except Exception as e:
            logger.error("cache_save_failed",
                        cache_path=str(cache_path),
                        error=str(e),
                        error_type=type(e).__name__,
                        impact="incremental_builds_disabled")
    
    def hash_file(self, file_path: Path) -> str:
        """
        Generate SHA256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex string of SHA256 hash
        """
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning("file_hash_failed",
                          file_path=str(file_path),
                          error=str(e),
                          error_type=type(e).__name__,
                          fallback="empty_hash")
            return ""
    
    def is_changed(self, file_path: Path) -> bool:
        """
        Check if a file has changed since last build.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is new or has changed, False if unchanged
        """
        if not file_path.exists():
            # File was deleted
            return True
        
        file_key = str(file_path)
        current_hash = self.hash_file(file_path)
        
        if file_key not in self.file_hashes:
            # New file
            return True
        
        # Check if hash changed
        return self.file_hashes[file_key] != current_hash
    
    def update_file(self, file_path: Path) -> None:
        """
        Update the hash for a file.
        
        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        self.file_hashes[file_key] = self.hash_file(file_path)
    
    def add_dependency(self, source: Path, dependency: Path) -> None:
        """
        Record that a source file depends on another file.
        
        Args:
            source: Source file (e.g., content page)
            dependency: Dependency file (e.g., template, partial, config)
        """
        source_key = str(source)
        dep_key = str(dependency)
        
        if source_key not in self.dependencies:
            self.dependencies[source_key] = set()
        
        self.dependencies[source_key].add(dep_key)
    
    def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None:
        """
        Record that a taxonomy term affects a page.
        
        Args:
            taxonomy_term: Taxonomy term (e.g., "tag:python")
            page: Page that uses this taxonomy term
        """
        if taxonomy_term not in self.taxonomy_deps:
            self.taxonomy_deps[taxonomy_term] = set()
        
        self.taxonomy_deps[taxonomy_term].add(str(page))
    
    def get_affected_pages(self, changed_file: Path) -> set[str]:
        """
        Find all pages that depend on a changed file.
        
        Args:
            changed_file: File that changed
            
        Returns:
            Set of page paths that need to be rebuilt
        """
        changed_key = str(changed_file)
        affected = set()
        
        # Check direct dependencies
        for source, deps in self.dependencies.items():
            if changed_key in deps:
                affected.add(source)
        
        # If the changed file itself is a source, rebuild it
        if changed_key in self.dependencies:
            affected.add(changed_key)
        
        return affected
    
    def get_previous_tags(self, page_path: Path) -> set[str]:
        """
        Get tags from previous build for a page.
        
        Args:
            page_path: Path to page
            
        Returns:
            Set of tags from previous build (empty set if new page)
        """
        return self.page_tags.get(str(page_path), set())
    
    def update_tags(self, page_path: Path, tags: set[str]) -> None:
        """
        Store current tags for a page (for next build's comparison).
        
        Args:
            page_path: Path to page
            tags: Current set of tags for the page
        """
        self.page_tags[str(page_path)] = tags
    
    def update_page_tags(self, page_path: Path, tags: set[str]) -> set[str]:
        """
        Update tag index when a page's tags change.
        
        Maintains bidirectional index:
        - page_tags: path → tags (forward)
        - tag_to_pages: tag → paths (inverted)
        
        This is the key method that enables O(1) taxonomy reconstruction.
        
        Args:
            page_path: Path to page source file
            tags: Current set of tags for this page (original case, e.g., "Python", "Web Dev")
            
        Returns:
            Set of affected tag slugs (tags added, removed, or modified)
        """
        page_path_str = str(page_path)
        affected_tags = set()
        
        # Get old tags for this page
        old_tags = self.page_tags.get(page_path_str, set())
        old_slugs = {tag.lower().replace(' ', '-') for tag in old_tags}
        new_slugs = {tag.lower().replace(' ', '-') for tag in tags}
        
        # Find changes
        removed_slugs = old_slugs - new_slugs
        added_slugs = new_slugs - old_slugs
        unchanged_slugs = old_slugs & new_slugs
        
        # Remove page from old tags
        for tag_slug in removed_slugs:
            if tag_slug in self.tag_to_pages:
                self.tag_to_pages[tag_slug].discard(page_path_str)
                # Remove empty tag entries
                if not self.tag_to_pages[tag_slug]:
                    del self.tag_to_pages[tag_slug]
                    self.known_tags.discard(tag_slug)
            affected_tags.add(tag_slug)
        
        # Add page to new tags
        for tag_slug in added_slugs:
            self.tag_to_pages.setdefault(tag_slug, set()).add(page_path_str)
            self.known_tags.add(tag_slug)
            affected_tags.add(tag_slug)
        
        # Mark unchanged tags as affected if page content changed
        # (affects sort order, which affects tag page rendering)
        affected_tags.update(unchanged_slugs)
        
        # Update forward index
        self.page_tags[page_path_str] = tags
        
        return affected_tags
    
    def get_pages_for_tag(self, tag_slug: str) -> set[str]:
        """
        Get all page paths for a given tag.
        
        Args:
            tag_slug: Tag slug (e.g., 'python', 'web-dev')
            
        Returns:
            Set of page path strings
        """
        return self.tag_to_pages.get(tag_slug, set()).copy()
    
    def get_all_tags(self) -> set[str]:
        """
        Get all known tag slugs from previous build.
        
        Returns:
            Set of tag slugs
        """
        return self.known_tags.copy()
    
    def clear(self) -> None:
        """Clear all cache data."""
        self.file_hashes.clear()
        self.dependencies.clear()
        self.output_sources.clear()
        self.taxonomy_deps.clear()
        self.page_tags.clear()
        self.tag_to_pages.clear()
        self.known_tags.clear()
        self.last_build = None
    
    def invalidate_file(self, file_path: Path) -> None:
        """
        Remove a file from the cache (useful when file is deleted).
        
        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        self.file_hashes.pop(file_key, None)
        self.dependencies.pop(file_key, None)
        
        # Remove as a dependency from other files
        for deps in self.dependencies.values():
            deps.discard(file_key)
        
        # Remove from taxonomy deps
        for deps in self.taxonomy_deps.values():
            deps.discard(file_key)
        
        # Remove page tags
        self.page_tags.pop(file_key, None)
    
    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics with logging.
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            'tracked_files': len(self.file_hashes),
            'dependencies': sum(len(deps) for deps in self.dependencies.values()),
            'taxonomy_terms': len(self.taxonomy_deps),
            'cached_content_pages': len(self.parsed_content),
        }
        
        logger.debug("cache_stats", **stats)
        return stats
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (f"BuildCache(files={stats['tracked_files']}, "
                f"deps={stats['dependencies']}, "
                f"taxonomies={stats['taxonomy_terms']})")
    
    # ========================================================================
    # OPTIMIZATION #2: Parsed Content Caching
    # ========================================================================
    
    def store_parsed_content(
        self,
        file_path: Path,
        html: str,
        toc: str,
        toc_items: list[dict[str, Any]],
        metadata: dict[str, Any],
        template: str,
        parser_version: str
    ) -> None:
        """
        Store parsed content in cache (Optimization #2).
        
        This allows skipping markdown parsing when only templates change,
        resulting in 20-30% faster builds in that scenario.
        
        Args:
            file_path: Path to source file
            html: Rendered HTML (post-markdown, pre-template)
            toc: Table of contents HTML
            toc_items: Structured TOC data
            metadata: Page metadata (frontmatter)
            template: Template name used
            parser_version: Parser version string (e.g., "mistune-3.0")
        """
        # Hash metadata to detect changes
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        
        # Calculate size for cache management
        size_bytes = len(html.encode('utf-8')) + len(toc.encode('utf-8'))
        
        # Store as dict (will be serialized to JSON)
        self.parsed_content[str(file_path)] = {
            'html': html,
            'toc': toc,
            'toc_items': toc_items,
            'metadata_hash': metadata_hash,
            'template': template,
            'parser_version': parser_version,
            'timestamp': datetime.now().isoformat(),
            'size_bytes': size_bytes
        }
    
    def get_parsed_content(
        self,
        file_path: Path,
        metadata: dict[str, Any],
        template: str,
        parser_version: str
    ) -> dict[str, Any] | None:
        """
        Get cached parsed content if valid (Optimization #2).
        
        Validates that:
        1. Content file hasn't changed (via file_hashes)
        2. Metadata hasn't changed (via metadata_hash)
        3. Template hasn't changed (via template name)
        4. Parser version matches (avoid incompatibilities)
        5. Template file hasn't changed (via dependencies)
        
        Args:
            file_path: Path to source file
            metadata: Current page metadata
            template: Current template name
            parser_version: Current parser version
            
        Returns:
            Cached data dict if valid, None if invalid or not found
        """
        key = str(file_path)
        
        # Check if cached
        if key not in self.parsed_content:
            return None
        
        cached = self.parsed_content[key]
        
        # Validate file hasn't changed
        if self.is_changed(file_path):
            return None
        
        # Validate metadata hasn't changed
        metadata_str = json.dumps(metadata, sort_keys=True, default=str)
        metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()
        if cached.get('metadata_hash') != metadata_hash:
            return None
        
        # Validate template hasn't changed (name)
        if cached.get('template') != template:
            return None
        
        # Validate parser version (invalidate on upgrades)
        if cached.get('parser_version') != parser_version:
            return None
        
        # Validate template file hasn't changed (via dependencies)
        # Check if any of the page's dependencies (templates) have changed
        if key in self.dependencies:
            for dep_path in self.dependencies[key]:
                dep = Path(dep_path)
                if dep.exists() and self.is_changed(dep):
                    # Template file changed - invalidate cache
                    return None
        
        return cached
    
    def invalidate_parsed_content(self, file_path: Path) -> None:
        """
        Remove cached parsed content for a file.
        
        Args:
            file_path: Path to file
        """
        self.parsed_content.pop(str(file_path), None)
    
    def get_parsed_content_stats(self) -> dict[str, Any]:
        """
        Get parsed content cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if not self.parsed_content:
            return {
                'cached_pages': 0,
                'total_size_mb': 0,
                'avg_size_kb': 0
            }
        
        total_size = sum(c.get('size_bytes', 0) for c in self.parsed_content.values())
        return {
            'cached_pages': len(self.parsed_content),
            'total_size_mb': total_size / 1024 / 1024,
            'avg_size_kb': (total_size / len(self.parsed_content) / 1024) if self.parsed_content else 0
        }

