"""Reactive dev pipeline for content-only edits.

When a single content file (leaf or section .md) is edited with content-only
changes (body changed, frontmatter unchanged), uses a reactive path instead of
the full build: incremental parse, re-render affected page(s), write to disk.
Skips discovery, provenance filter, assets, post-process, and cache save.
"""

from bengal.server.reactive.handler import ReactiveContentHandler, ReactiveResult

__all__ = ["ReactiveContentHandler", "ReactiveResult"]
