# logger

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/logger.py

Structured logging system for Bengal SSG.

Provides phase-aware logging with context propagation, timing,
and structured event emission. Designed for observability into
the 22-phase build pipeline.

Example:
    from bengal.utils.logger import get_logger

    logger = get_logger(__name__)

    with logger.phase("discovery", page_count=100):
        logger.info("discovered_content", files=len(files))
        logger.debug("parsed_frontmatter", page=page.path, keys=list(metadata.keys()))

*Note: Template has undefined variables. This is fallback content.*
