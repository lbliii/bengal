"""
External References for Bengal SSG.

Provides cross-project documentation linking using [[ext:project:target]] syntax.

Architecture:
Three-tier resolution:
1. URL Templates (Instant, Offline) - Pattern-based URL construction
2. Bengal Index (Cached, Async) - Fetch xref.json from Bengal sites
3. Graceful Fallback - Render as code + warning (never breaks build)

Usage:
    ```markdown
    [[ext:python:pathlib.Path]]              # URL template resolution
    [[ext:kida:Markup]]                      # Bengal ecosystem index
    [[ext:numpy:ndarray|NumPy Arrays]]       # Custom link text
    ```

Configuration:
    ```toml
    [external_refs]
    enabled = true
    export_index = true  # Generate xref.json on production builds

    [external_refs.templates]
    python = "https://docs.python.org/3/library/{module}.html#{name}"

    [[external_refs.indexes]]
    name = "kida"
    url = "https://lbliii.github.io/kida/xref.json"
    cache_days = 7
    ```

Components:
- ExternalRefResolver: Main resolver class
- IndexCache: Cached index fetching with stale-while-revalidate
- resolve_template: URL template expansion

Related:
- bengal.rendering.plugins.cross_references: Integration point
- bengal.postprocess.xref_index: xref.json exporter
- plan/rfc-external-references.md: RFC for this feature

See Also:
- https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

"""

from bengal.rendering.external_refs.resolver import (
    ExternalRefResolver,
    resolve_template,
)

__all__ = [
    "ExternalRefResolver",
    "resolve_template",
]
