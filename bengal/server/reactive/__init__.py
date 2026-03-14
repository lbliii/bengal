"""Reactive dev pipeline for content-only and template-only edits.

When a single content file (leaf or section .md) is edited with content-only
changes (body changed, frontmatter unchanged), uses a reactive path instead of
the full build: incremental parse, re-render affected page(s), write to disk.
Skips discovery, provenance filter, assets, post-process, and cache save.

When templates (.html) change, re-renders only affected pages via
ReactiveTemplateHandler instead of full discovery + build.
"""

from bengal.server.reactive.handler import ReactiveContentHandler, ReactiveResult
from bengal.server.reactive.template_handler import (
    ReactiveTemplateHandler,
    TemplateReactiveResult,
)

__all__ = [
    "ReactiveContentHandler",
    "ReactiveResult",
    "ReactiveTemplateHandler",
    "TemplateReactiveResult",
]
