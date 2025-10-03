"""
Build Cache - Tracks file changes and dependencies for incremental builds.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, Optional, List
import hashlib
import json
from datetime import datetime


@dataclass
class BuildCache:
    """
    Tracks file hashes and dependencies between builds.
    
    Attributes:
        file_hashes: Mapping of file paths to their SHA256 hashes
        dependencies: Mapping of pages to their dependencies (templates, partials, etc.)
        output_sources: Mapping of output files to their source files
        taxonomy_deps: Mapping of taxonomy terms to affected pages
        last_build: Timestamp of last successful build
    """
    
    file_hashes: Dict[str, str] = field(default_factory=dict)
    dependencies: Dict[str, Set[str]] = field(default_factory=dict)
    output_sources: Dict[str, str] = field(default_factory=dict)
    taxonomy_deps: Dict[str, Set[str]] = field(default_factory=dict)
    last_build: Optional[str] = None
    
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
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert lists back to sets in dependencies
            if 'dependencies' in data:
                data['dependencies'] = {
                    k: set(v) for k, v in data['dependencies'].items()
                }
            
            if 'taxonomy_deps' in data:
                data['taxonomy_deps'] = {
                    k: set(v) for k, v in data['taxonomy_deps'].items()
                }
            
            return cls(**data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to load cache from {cache_path}: {e}")
            print("Starting with fresh cache")
            return cls()
    
    def save(self, cache_path: Path) -> None:
        """
        Save build cache to disk.
        
        Args:
            cache_path: Path to cache file
        """
        # Ensure parent directory exists
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert sets to lists for JSON serialization
        data = {
            'file_hashes': self.file_hashes,
            'dependencies': {k: list(v) for k, v in self.dependencies.items()},
            'output_sources': self.output_sources,
            'taxonomy_deps': {k: list(v) for k, v in self.taxonomy_deps.items()},
            'last_build': datetime.now().isoformat()
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache to {cache_path}: {e}")
    
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
            print(f"Warning: Failed to hash file {file_path}: {e}")
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
    
    def get_affected_pages(self, changed_file: Path) -> Set[str]:
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
    
    def clear(self) -> None:
        """Clear all cache data."""
        self.file_hashes.clear()
        self.dependencies.clear()
        self.output_sources.clear()
        self.taxonomy_deps.clear()
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
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'tracked_files': len(self.file_hashes),
            'dependencies': sum(len(deps) for deps in self.dependencies.values()),
            'taxonomy_terms': len(self.taxonomy_deps),
        }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (f"BuildCache(files={stats['tracked_files']}, "
                f"deps={stats['dependencies']}, "
                f"taxonomies={stats['taxonomy_terms']})")

