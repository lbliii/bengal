Completed OpenAPI autodoc Phase 2. Endpoint pages now render a cross-endpoint
sidebar that marks the current endpoint with both an `--active` class and
`aria-current="page"`. The endpoint/schema templates were migrated from
Jinja-era `{% include %}` partials to Kida `{% def %}`/`{% slot %}` components
(`_components.html`, recursive `_schema.html`) with no change to rendered
output. Multi-tag endpoints are now cross-listed under every one of their tag
sections (previously a secondary tag that also owned its own endpoint silently
dropped the cross-listed ones), still backed by a single canonical page, and
their header tag chips link to the correct per-tag section URL.
