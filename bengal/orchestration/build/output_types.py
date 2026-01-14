"""
Output type classification for Bengal SSG.

RFC: Output Cache Architecture - Categorizes all output files for appropriate
caching and hot reload strategies.

Output Types:
- CONTENT_PAGE: HTML from .md source files (fully cacheable)
- GENERATED_PAGE: Tag pages, section archives, API docs (cache by member hashes)
- AGGREGATE_INDEX: index.json, search index (always regenerated, hashable)
- AGGREGATE_FEED: rss.xml, atom.xml, sitemap.xml (always regenerated, hashable)
- AGGREGATE_TEXT: llm-full.txt, index.txt (always regenerated, hashable)
- ASSET: CSS, JS, images (fingerprinted separately)
- STATIC: favicon, robots.txt (copied verbatim)

Usage:
    from bengal.orchestration.build.output_types import OutputType, classify_output
    
    output_type = classify_output(Path("public/docs/index.html"))
    if output_type == OutputType.AGGREGATE_FEED:
        # Don't trigger hot reload for aggregate changes
        pass

Related Modules:
- bengal.rendering.pipeline.output: Uses for content hash decisions
- bengal.server.reload_controller: Uses for change categorization
- bengal.cache.generated_page_cache: Uses for cache strategy selection

"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class OutputType(Enum):
    """
    Classification of output files for caching strategy.
    
    RFC: Output Cache Architecture - Each type has different caching and
    hot reload behavior.
    
    Attributes:
        CONTENT_PAGE: HTML from .md source files - fully cacheable
        GENERATED_PAGE: Tag pages, section archives, API docs - cache by member hashes
        AGGREGATE_INDEX: index.json, search index - always regenerated
        AGGREGATE_FEED: rss.xml, atom.xml, sitemap.xml - always regenerated
        AGGREGATE_TEXT: llm-full.txt, index.txt - always regenerated
        ASSET: CSS, JS, images - fingerprinted separately
        STATIC: favicon, robots.txt - copied verbatim
        
    """
    
    # Content pages - can be fully cached
    CONTENT_PAGE = auto()      # HTML from .md source files
    GENERATED_PAGE = auto()    # Tag pages, section archives, API docs
    
    # Aggregate outputs - always regenerated, but content-hashable
    AGGREGATE_INDEX = auto()   # index.json, search index
    AGGREGATE_FEED = auto()    # rss.xml, atom.xml, sitemap.xml
    AGGREGATE_TEXT = auto()    # llm-full.txt, index.txt
    
    # Static assets - fingerprinted separately
    ASSET = auto()             # CSS, JS, images
    
    # Passthrough - copied verbatim
    STATIC = auto()            # favicon, robots.txt


# File patterns for classification (exact filename matches)
OUTPUT_PATTERNS: dict[str, OutputType] = {
    # Aggregates (always regenerate, but hash content)
    "sitemap.xml": OutputType.AGGREGATE_FEED,
    "rss.xml": OutputType.AGGREGATE_FEED,
    "atom.xml": OutputType.AGGREGATE_FEED,
    "index.json": OutputType.AGGREGATE_INDEX,
    "index.json.hash": OutputType.AGGREGATE_INDEX,
    "llm-full.txt": OutputType.AGGREGATE_TEXT,
    "index.txt": OutputType.AGGREGATE_TEXT,
    
    # Static assets with known names
    "asset-manifest.json": OutputType.ASSET,
    
    # Static files (passthrough)
    "favicon.ico": OutputType.STATIC,
    "robots.txt": OutputType.STATIC,
    ".nojekyll": OutputType.STATIC,
    "CNAME": OutputType.STATIC,
}

# Directory patterns for classification
ASSET_DIRS = {"assets", "static", "css", "js", "images", "fonts"}


def classify_output(path: Path, metadata: dict[str, Any] | None = None) -> OutputType:
    """
    Classify an output file by type.
    
    RFC: Output Cache Architecture - Determines caching strategy and hot reload
    behavior for each output file.
    
    Classification order:
    1. Explicit filename patterns (sitemap.xml, index.json, etc.)
    2. Page metadata (_generated flag)
    3. File extension (.html → CONTENT_PAGE)
    4. Directory location (assets/ → ASSET)
    5. Default to STATIC
    
    Args:
        path: Path to the output file
        metadata: Optional page metadata dict for generated page detection
    
    Returns:
        OutputType enum value
        
    Examples:
        >>> classify_output(Path("public/sitemap.xml"))
        OutputType.AGGREGATE_FEED
        
        >>> classify_output(Path("public/docs/index.html"))
        OutputType.CONTENT_PAGE
        
        >>> classify_output(Path("public/tags/python/index.html"), {"_generated": True})
        OutputType.GENERATED_PAGE
        
    """
    name = path.name
    
    # Check explicit patterns first (exact filename match)
    if name in OUTPUT_PATTERNS:
        return OUTPUT_PATTERNS[name]
    
    # Check metadata for generated pages
    if metadata and metadata.get("_generated"):
        return OutputType.GENERATED_PAGE
    
    # HTML files are content pages by default
    if path.suffix == ".html":
        return OutputType.CONTENT_PAGE
    
    # Assets in asset directories
    parts_lower = {p.lower() for p in path.parts}
    if parts_lower & ASSET_DIRS:
        return OutputType.ASSET
    
    # CSS/JS files are assets regardless of location
    if path.suffix in {".css", ".js", ".mjs"}:
        return OutputType.ASSET
    
    # Image files are assets
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}:
        return OutputType.ASSET
    
    # Font files are assets
    if path.suffix.lower() in {".woff", ".woff2", ".ttf", ".eot", ".otf"}:
        return OutputType.ASSET
    
    return OutputType.STATIC


def is_aggregate_output(output_type: OutputType) -> bool:
    """
    Check if output type is an aggregate (always regenerated).
    
    Aggregate outputs shouldn't trigger hot reload by themselves since
    they change on every build regardless of content changes.
    
    Args:
        output_type: OutputType to check
    
    Returns:
        True if aggregate type
        
    """
    return output_type in {
        OutputType.AGGREGATE_INDEX,
        OutputType.AGGREGATE_FEED,
        OutputType.AGGREGATE_TEXT,
    }


def is_content_output(output_type: OutputType) -> bool:
    """
    Check if output type represents user-visible content.
    
    Content changes should trigger hot reload.
    
    Args:
        output_type: OutputType to check
    
    Returns:
        True if content type (CONTENT_PAGE or GENERATED_PAGE)
        
    """
    return output_type in {
        OutputType.CONTENT_PAGE,
        OutputType.GENERATED_PAGE,
    }
