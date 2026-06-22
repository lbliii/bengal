`:::{include}` and `:::{literalinclude}` now render included markdown and code as HTML instead of showing raw fenced blocks on the page.

Includes are expanded at render time with nested-directive support, cycle/depth guards, mtime-keyed snippet caching, effect-traced dependencies for incremental rebuilds, health check H208 for broken paths, and `bengal debug includes <page>` for inspection.
