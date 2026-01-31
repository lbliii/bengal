"""
Rendering pipeline package for Bengal SSG.

Orchestrates the parsing, AST building, templating, and output rendering phases
for individual pages. Manages thread-local parser instances for performance
and provides dependency tracking for incremental builds.

Public API:
- RenderingPipeline: Main pipeline class for page rendering
- extract_toc_structure: Parse TOC HTML into structured data
- TOC_EXTRACTION_VERSION: Version for cache invalidation

The pipeline is composed of focused modules:
- core.py: Main RenderingPipeline class
- thread_local.py: Thread-local parser management
- toc.py: TOC extraction utilities
- transforms.py: Content transformations
- output.py: Output handling

Usage:

```python
from bengal.rendering.pipeline import RenderingPipeline

pipeline = RenderingPipeline(site, dependency_tracker=tracker)
pipeline.process_page(page)
```

Related Modules:
- bengal.parsing: Markdown parser implementations
- bengal.rendering.template_engine: Template rendering (Kida default)
- bengal.rendering.renderer: Page rendering logic
- bengal.build.tracking: Dependency tracking

"""

from __future__ import annotations

from bengal.rendering.pipeline.core import RenderingPipeline
from bengal.rendering.pipeline.toc import TOC_EXTRACTION_VERSION, extract_toc_structure
from bengal.rendering.pipeline.write_behind import WriteBehindCollector

__all__ = [
    "TOC_EXTRACTION_VERSION",
    "RenderingPipeline",
    "WriteBehindCollector",
    "extract_toc_structure",
]
