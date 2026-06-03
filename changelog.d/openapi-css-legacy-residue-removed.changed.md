Removed the dead pre-shell REST/OpenAPI layout CSS from the default theme's
`autodoc.css` (~1450 lines): the Mintlify explorer grid, the three-column
`.api-explorer` layout, the single-column `.api-reference` layout, the standalone
`.api-home` landing page, and the `.api-playground` bar. These layers were
superseded by the bespoke `.api-catalog-app` / `.openapi-app` shell, which now
owns every rendered REST page — verified by a zero-occurrence grep of all
issue-named legacy classes across the generated `bengal-demo-commerce` site and a
byte-stable live-class histogram before/after the change. Each deletion was
cross-checked against the emitted-class set so live shell selectors (and shared
typography/card groups) are preserved; structural rules (`#main-content` reset,
global `.breadcrumb__item`) are untouched. Two orphaned templates
(`partials/playground-bar.html`, the superseded `partials/endpoint-header.html`)
were also deleted, and a discriminating contract test now fails if any legacy
selector reappears.
