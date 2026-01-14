"""
Content hash registry for Bengal SSG.

RFC: Output Cache Architecture - Central registry mapping outputs to their
content hashes for cross-build validation.

Key Features:
- O(1) lookup for output change validation
- Dependency tracking for generated pages
- Format versioning for compatibility
- Corruption recovery with graceful fallback
- Thread-safe updates via RLock

Performance:
- <1ms validation for 1000+ page sites
- Compressed persistence (92-93% smaller with Zstandard)
- Incremental updates (only changed entries)

Thread Safety:
Internal mappings are protected by an RLock for safe concurrent access
during parallel rendering updates.

Usage:
    from bengal.cache.content_hash_registry import ContentHashRegistry
    
    registry = ContentHashRegistry.load(site.paths.content_hash_registry)
    registry.update_source(page.source_path, content_hash)
    registry.update_output(output_path, output_hash, OutputType.CONTENT_PAGE)
    registry.save(site.paths.content_hash_registry)
    
    # Validate cache integrity
    is_valid, message = ContentHashRegistry.validate(site.paths.content_hash_registry)

Related Modules:
- bengal.rendering.pipeline.output: Content hash embedding
- bengal.server.reload_controller: Uses for change detection
- bengal.orchestration.build.output_types: Output type classification
- bengal.cache.generated_page_cache: Uses for member hash lookups

"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger
from bengal.utils.primitives.hashing import hash_str

if TYPE_CHECKING:
    from bengal.orchestration.build.output_types import OutputType

logger = get_logger(__name__)

# Cache format version - increment when schema changes
REGISTRY_FORMAT_VERSION = 1


@dataclass
class ContentHashRegistry:
    """
    Central registry mapping outputs to their content hashes.
    
    RFC: Output Cache Architecture - Provides O(1) lookup for:
    - Validating if output changed
    - Finding dependencies of generated pages
    - Computing aggregate hashes for cache keys
    
    Persisted to .bengal/content_hashes.json.zst for cross-build validation.
    
    Thread Safety:
    Internal mappings are protected by an RLock for safe concurrent access
    during parallel rendering updates.
    
    Attributes:
        version: Format version for compatibility checking
        source_hashes: Source file → content hash mapping
        output_hashes: Output file → content hash mapping
        output_types: Output file → OutputType name mapping
        generated_dependencies: Generated page → list of source paths
        
    Example:
        >>> registry = ContentHashRegistry.load(paths.content_hash_registry)
        >>> registry.update_source(Path("content/post.md"), "abc123...")
        >>> registry.save(paths.content_hash_registry)
        
    """
    
    # Format version for compatibility checking
    version: int = REGISTRY_FORMAT_VERSION
    
    # Source file → content hash (for content pages)
    source_hashes: dict[str, str] = field(default_factory=dict)
    
    # Output file → content hash (for all outputs)
    output_hashes: dict[str, str] = field(default_factory=dict)
    
    # Output file → OutputType name (string for serialization)
    output_types: dict[str, str] = field(default_factory=dict)
    
    # Generated page path → list of source paths it depends on
    generated_dependencies: dict[str, list[str]] = field(default_factory=dict)
    
    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    
    # Dirty flag for incremental saves
    _dirty: bool = field(default=False, repr=False)
    
    def update_source(self, source_path: Path, content_hash: str) -> None:
        """
        Update hash for a source file.
        
        Args:
            source_path: Path to source file
            content_hash: Hash of file content
            
        """
        with self._lock:
            self.source_hashes[str(source_path)] = content_hash
            self._dirty = True
    
    def update_output(
        self,
        output_path: Path,
        content_hash: str,
        output_type: OutputType | str,
    ) -> None:
        """
        Update hash for an output file.
        
        Args:
            output_path: Path to output file
            content_hash: Hash of rendered content
            output_type: OutputType enum or name string
            
        """
        key = str(output_path)
        type_name = output_type.name if hasattr(output_type, "name") else str(output_type)
        
        with self._lock:
            self.output_hashes[key] = content_hash
            self.output_types[key] = type_name
            self._dirty = True
    
    def update_generated_deps(
        self,
        generated_path: Path,
        member_sources: list[Path],
    ) -> None:
        """
        Track dependencies for generated page.
        
        Args:
            generated_path: Path to generated page output
            member_sources: List of source paths this page depends on
            
        """
        with self._lock:
            self.generated_dependencies[str(generated_path)] = [
                str(p) for p in member_sources
            ]
            self._dirty = True
    
    def get_source_hash(self, source_path: Path) -> str | None:
        """Get content hash for a source file."""
        with self._lock:
            return self.source_hashes.get(str(source_path))
    
    def get_output_hash(self, output_path: Path) -> str | None:
        """Get content hash for an output file."""
        with self._lock:
            return self.output_hashes.get(str(output_path))
    
    def get_member_hashes(self, generated_path: Path) -> dict[str, str]:
        """
        Get content hashes for all members of generated page.
        
        Args:
            generated_path: Path to generated page
        
        Returns:
            Mapping of source_path → content_hash for dependencies
            
        """
        with self._lock:
            deps = self.generated_dependencies.get(str(generated_path), [])
            return {
                dep: self.source_hashes.get(dep, "")
                for dep in deps
            }
    
    def compute_generated_hash(self, generated_path: Path) -> str:
        """
        Compute combined hash for generated page validation.
        
        Args:
            generated_path: Path to generated page
        
        Returns:
            Combined hash of all member content hashes
            
        """
        member_hashes = self.get_member_hashes(generated_path)
        combined = "|".join(sorted(member_hashes.values()))
        return hash_str(combined, truncate=16)
    
    def has_changed(self, output_path: Path, current_hash: str) -> bool:
        """
        Check if output has changed from registered hash.
        
        Args:
            output_path: Path to check
            current_hash: Current content hash
        
        Returns:
            True if hash differs or not registered
            
        """
        with self._lock:
            registered = self.output_hashes.get(str(output_path))
            return registered is None or registered != current_hash
    
    def save(self, path: Path) -> None:
        """
        Persist registry to disk with version metadata.
        
        Uses compressed format (.json.zst) for 92-93% size reduction.
        
        Args:
            path: Path to save to (base path, .zst added automatically)
            
        """
        if not self._dirty:
            return
        
        try:
            from bengal.cache.compression import save_compressed
            
            with self._lock:
                data = {
                    "version": REGISTRY_FORMAT_VERSION,
                    "source_hashes": self.source_hashes,
                    "output_hashes": self.output_hashes,
                    "output_types": self.output_types,
                    "generated_dependencies": self.generated_dependencies,
                }
            
            # Save to .json.zst
            zst_path = path.with_suffix(".json.zst") if not path.name.endswith(".zst") else path
            save_compressed(data, zst_path)
            self._dirty = False
            
            logger.debug(
                "content_hash_registry_saved",
                sources=len(self.source_hashes),
                outputs=len(self.output_hashes),
                path=str(zst_path),
            )
            
        except Exception as e:
            logger.warning(
                "content_hash_registry_save_failed",
                path=str(path),
                error=str(e),
                error_type=type(e).__name__,
            )
    
    @classmethod
    def load(cls, path: Path) -> ContentHashRegistry:
        """
        Load registry from disk with version check and corruption recovery.
        
        Recovery Behavior:
        - Missing file: Return empty registry (normal for first build)
        - Corrupted JSON: Log warning, return empty registry
        - Version mismatch: Log info, return empty registry (will rebuild)
        - Missing fields: Use defaults for forward compatibility
        
        Args:
            path: Path to registry file
        
        Returns:
            ContentHashRegistry instance
            
        """
        # Try compressed first, then uncompressed
        zst_path = path.with_suffix(".json.zst") if not path.name.endswith(".zst") else path
        json_path = path if path.suffix == ".json" else path.with_suffix(".json")
        
        if not zst_path.exists() and not json_path.exists():
            return cls()
        
        try:
            from bengal.cache.compression import load_auto
            
            data = load_auto(json_path)
            
            # Check format version
            file_version = data.get("version", 0)
            if file_version < REGISTRY_FORMAT_VERSION:
                logger.info(
                    "content_hash_registry_version_mismatch",
                    file_version=file_version,
                    current_version=REGISTRY_FORMAT_VERSION,
                    action="rebuilding_registry",
                )
                return cls()
            
            registry = cls(
                version=file_version,
                source_hashes=data.get("source_hashes", {}),
                output_hashes=data.get("output_hashes", {}),
                output_types=data.get("output_types", {}),
                generated_dependencies=data.get("generated_dependencies", {}),
            )
            
            logger.debug(
                "content_hash_registry_loaded",
                sources=len(registry.source_hashes),
                outputs=len(registry.output_hashes),
            )
            
            return registry
            
        except json.JSONDecodeError as e:
            logger.warning(
                "content_hash_registry_corrupted",
                path=str(path),
                error=str(e),
                action="starting_fresh",
            )
            return cls()
            
        except FileNotFoundError:
            return cls()
            
        except Exception as e:
            logger.warning(
                "content_hash_registry_load_failed",
                path=str(path),
                error_type=type(e).__name__,
                error=str(e),
                action="starting_fresh",
            )
            return cls()
    
    @classmethod
    def validate(cls, path: Path) -> tuple[bool, str]:
        """
        Validate registry file integrity.
        
        Use with `bengal cache validate` for explicit verification.
        
        Args:
            path: Path to registry file
        
        Returns:
            Tuple of (is_valid, message)
            
        """
        zst_path = path.with_suffix(".json.zst") if not path.name.endswith(".zst") else path
        json_path = path if path.suffix == ".json" else path.with_suffix(".json")
        
        if not zst_path.exists() and not json_path.exists():
            return True, "No registry file (will be created on build)"
        
        try:
            from bengal.cache.compression import load_auto
            
            data = load_auto(json_path)
            
            # Check version
            version = data.get("version", 0)
            if version != REGISTRY_FORMAT_VERSION:
                return False, f"Version mismatch: {version} != {REGISTRY_FORMAT_VERSION}"
            
            # Check required fields
            required = ["source_hashes", "output_hashes"]
            missing = [f for f in required if f not in data]
            if missing:
                return False, f"Missing fields: {missing}"
            
            # Check data types
            if not isinstance(data.get("source_hashes"), dict):
                return False, "source_hashes is not a dict"
            if not isinstance(data.get("output_hashes"), dict):
                return False, "output_hashes is not a dict"
            
            return True, f"Valid (version {version}, {len(data['source_hashes'])} sources)"
            
        except json.JSONDecodeError as e:
            return False, f"JSON parse error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def clear(self) -> None:
        """Clear all registry data."""
        with self._lock:
            self.source_hashes.clear()
            self.output_hashes.clear()
            self.output_types.clear()
            self.generated_dependencies.clear()
            self._dirty = True
        
        logger.info("content_hash_registry_cleared")
    
    def get_stats(self) -> dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
            
        """
        with self._lock:
            return {
                "version": self.version,
                "source_count": len(self.source_hashes),
                "output_count": len(self.output_hashes),
                "generated_deps_count": len(self.generated_dependencies),
                "output_types": self._count_output_types(),
            }
    
    def _count_output_types(self) -> dict[str, int]:
        """Count outputs by type."""
        counts: dict[str, int] = {}
        for type_name in self.output_types.values():
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
