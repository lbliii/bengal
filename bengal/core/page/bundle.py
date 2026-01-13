"""Page bundle detection and resource access.

Page bundles keep content and assets together in a directory:
- Leaf bundles: posts/my-post/index.md (page with co-located resources)
- Branch bundles: posts/_index.md (section index, no resources)
- Regular pages: posts/my-post.md (standalone file, no bundle resources)

This module provides:
- BundleType enum for bundle classification
- PageBundleMixin for Page integration
- PageResources collection for accessing co-located files
- PageResource for individual resource files

Example:
    >>> page = Page(source_path=Path("posts/my-post/index.md"))
    >>> page.bundle_type
<BundleType.LEAF: 'leaf'>
    >>> page.is_bundle
True
    >>> hero = page.resources.get_match("hero.*")
    >>> hero.as_image().fill("800x600 webp")

"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# MIME type category mappings
_TYPE_EXTENSIONS: dict[str, set[str]] = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".avif", ".ico", ".bmp", ".tiff"},
    "video": {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"},
    "document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
    "data": {".json", ".yaml", ".yml", ".csv", ".xml", ".toml"},
    "code": {".js", ".ts", ".css", ".scss", ".less", ".py", ".rb", ".go"},
    "archive": {".zip", ".tar", ".gz", ".rar", ".7z"},
}

# Extensions to exclude from bundle resources (content files)
_CONTENT_EXTENSIONS: set[str] = {".md", ".markdown", ".rst", ".txt"}


class BundleType(Enum):
    """Type of content bundle.
    
    Bundle classification based on filename convention:
    - NONE: Regular standalone page (my-post.md)
    - LEAF: Leaf bundle with resources (my-post/index.md)
    - BRANCH: Branch bundle / section index (_index.md)
        
    """

    NONE = "none"  # Regular page (my-post.md)
    LEAF = "leaf"  # Leaf bundle (my-post/index.md)
    BRANCH = "branch"  # Branch bundle (_index.md)


@dataclass(frozen=True)
class PageResource:
    """Single resource co-located with a page bundle.
    
    Represents a non-content file in a leaf bundle directory
    (images, data files, PDFs, etc.).
    
    Attributes:
        path: Absolute path to the resource file
        page_url: URL of the parent page (for rel_permalink)
    
    Example:
            >>> resource = PageResource(path=Path("/site/posts/my-post/hero.jpg"), page_url="/posts/my-post/")
            >>> resource.name
            'hero.jpg'
            >>> resource.rel_permalink
            '/posts/my-post/hero.jpg'
        
    """

    path: Path
    page_url: str

    @property
    def name(self) -> str:
        """Filename with extension."""
        return self.path.name

    @property
    def stem(self) -> str:
        """Filename without extension."""
        return self.path.stem

    @property
    def suffix(self) -> str:
        """File extension including dot (e.g., '.jpg')."""
        return self.path.suffix

    @property
    def rel_permalink(self) -> str:
        """URL relative to site root.

        Resources are served alongside the page.
        """
        # Ensure page_url ends with /
        page_url = self.page_url.rstrip("/") + "/" if self.page_url else "/"
        return f"{page_url}{self.name}"

    @property
    def size(self) -> int:
        """File size in bytes."""
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    @property
    def exists(self) -> bool:
        """Check if the resource file exists."""
        return self.path.exists()

    @property
    def resource_type(self) -> str | None:
        """Get resource type category based on extension.

        Returns one of: 'image', 'video', 'audio', 'document', 'data', 'code', 'archive'
        or None if unrecognized.
        """
        suffix_lower = self.suffix.lower()
        for category, extensions in _TYPE_EXTENSIONS.items():
            if suffix_lower in extensions:
                return category
        return None

    def as_image(self) -> Any | None:
        """Convert to ImageResource for image processing.

        Returns None if not an image file or if image processing
        is not available.

        Note: ImageResource is imported lazily to avoid circular imports
        and to make image processing optional.
        """
        if self.suffix.lower() not in _TYPE_EXTENSIONS.get("image", set()):
            return None

        try:
            from bengal.core.resources.image import ImageResource

            # ImageResource needs the site for processing, but we don't have it here.
            # Return a minimal ImageResource that can be used for basic operations.
            return ImageResource(source_path=self.path, site=None)
        except ImportError:
            # Image processing module not available
            return None

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read resource as text (for data files)."""
        return self.path.read_text(encoding=encoding)

    def read_bytes(self) -> bytes:
        """Read resource as bytes (for binary files)."""
        return self.path.read_bytes()

    def read_json(self) -> Any:
        """Read resource as JSON.

        Returns parsed JSON data.
        """
        import json

        return json.loads(self.read_text())

    def read_yaml(self) -> Any:
        """Read resource as YAML.

        Returns parsed YAML data.
        """
        try:
            import yaml

            return yaml.safe_load(self.read_text())
        except ImportError as err:
            raise ImportError(
                "PyYAML is required for read_yaml(). Install with: pip install pyyaml"
            ) from err

    def __str__(self) -> str:
        """Return URL for easy template usage."""
        return self.rel_permalink


@dataclass
class PageResources:
    """Collection of resources co-located with a page bundle.
    
    Provides resource access methods for leaf bundles including
    pattern matching and type-based filtering.
    Empty collection for non-bundle pages.
    
    Attributes:
        _resources: Internal list of PageResource objects
        _by_name: Lookup dict keyed by filename
    
    Example:
            >>> resources = page.resources
            >>> hero = resources.get_match("hero.*")
            >>> images = resources.by_type("image")
            >>> data = resources.get("config.json")
        
    """

    _resources: list[PageResource] = field(default_factory=list)
    _by_name: dict[str, PageResource] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Build lookup dict from resources."""
        self._by_name = {r.name: r for r in self._resources}

    def get(self, name: str) -> PageResource | None:
        """Get resource by exact filename.

        Args:
            name: Exact filename to match (e.g., "hero.jpg")

        Returns:
            PageResource if found, None otherwise

        Example:
            >>> page.resources.get("data.json")
        """
        return self._by_name.get(name)

    def get_match(self, pattern: str) -> PageResource | None:
        """Get first resource matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "hero.*", "*.pdf")

        Returns:
            First matching PageResource, or None

        Example:
            >>> page.resources.get_match("hero.*")  # hero.jpg, hero.png, etc.
            >>> page.resources.get_match("diagram-*.svg")
        """
        for r in self._resources:
            if fnmatch.fnmatch(r.name, pattern):
                return r
        return None

    def match(self, pattern: str) -> list[PageResource]:
        """Get all resources matching glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.jpg", "gallery-*")

        Returns:
            List of matching PageResource objects

        Example:
            >>> page.resources.match("gallery-*.jpg")
            >>> page.resources.match("*.pdf")
        """
        return [r for r in self._resources if fnmatch.fnmatch(r.name, pattern)]

    def by_type(self, resource_type: str) -> list[PageResource]:
        """Get resources by MIME type category.

        Args:
            resource_type: One of 'image', 'video', 'audio', 'document', 'data', 'code', 'archive'

        Returns:
            List of matching PageResource objects

        Example:
            >>> page.resources.by_type("image")
            >>> page.resources.by_type("data")
        """
        extensions = _TYPE_EXTENSIONS.get(resource_type, set())
        return [r for r in self._resources if r.suffix.lower() in extensions]

    def images(self) -> list[PageResource]:
        """Get all image resources. Convenience alias for by_type("image")."""
        return self.by_type("image")

    def data(self) -> list[PageResource]:
        """Get all data resources (JSON, YAML, CSV, etc.). Convenience alias for by_type("data")."""
        return self.by_type("data")

    def __iter__(self):
        """Iterate over all resources."""
        return iter(self._resources)

    def __len__(self) -> int:
        """Number of resources."""
        return len(self._resources)

    def __bool__(self) -> bool:
        """True if there are any resources."""
        return len(self._resources) > 0

    def __contains__(self, name: str) -> bool:
        """Check if resource exists by name."""
        return name in self._by_name


class PageBundleMixin:
    """Mixin providing bundle detection and resource access for Page.
    
    Add to Page's inheritance chain to enable:
    - bundle_type: BundleType classification
    - is_bundle: Quick check for leaf bundle
    - resources: PageResources collection
    
    Required attributes on host class:
    - source_path: Path to the source markdown file
    - url: Page URL (for resource permalinks)
        
    """

    # These will be defined on the host Page class
    source_path: Path
    url: str

    @cached_property
    def bundle_type(self) -> BundleType:
        """Determine bundle type from file structure.

        - index.md in directory → LEAF (has resources)
        - _index.md in directory → BRANCH (section, no resources)
        - standalone .md file → NONE

        Returns:
            BundleType enum value
        """
        name = self.source_path.name.lower()

        if name == "index.md":
            return BundleType.LEAF
        elif name == "_index.md":
            return BundleType.BRANCH
        else:
            return BundleType.NONE

    @property
    def is_bundle(self) -> bool:
        """True if this page is a leaf bundle with resources.

        Only leaf bundles (index.md) have co-located resources.
        Branch bundles (_index.md) are section indexes without resources.
        """
        return self.bundle_type == BundleType.LEAF

    @property
    def is_branch_bundle(self) -> bool:
        """True if this page is a branch bundle (section index)."""
        return self.bundle_type == BundleType.BRANCH

    @cached_property
    def resources(self) -> PageResources:
        """Get resources co-located with this page.

        For leaf bundles (index.md in directory), returns all
        non-markdown files in the same directory.

        Returns empty PageResources for non-bundles (not an error).

        Returns:
            PageResources collection (empty if not a bundle)

        Example:
            >>> page.resources.get_match("hero.*")
            >>> page.resources.by_type("image")
        """
        if not self.is_bundle:
            return PageResources([])

        bundle_dir = self.source_path.parent

        if not bundle_dir.exists() or not bundle_dir.is_dir():
            return PageResources([])

        resources: list[PageResource] = []

        for path in bundle_dir.iterdir():
            if not path.is_file():
                continue

            # Skip content files
            if path.suffix.lower() in _CONTENT_EXTENSIONS:
                continue

            resources.append(
                PageResource(
                    path=path,
                    page_url=getattr(self, "url", "/"),
                )
            )

        # Sort by name for deterministic ordering
        resources.sort(key=lambda r: r.name)

        return PageResources(resources)
