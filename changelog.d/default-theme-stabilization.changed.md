The bundled `default` theme no longer ships dead or demo-only assets: the
39-file `icons_backup/` directory, two orphaned holographic-card demo pages,
and several stale architecture/process docs are removed. The experimental
holographic-card CSS is no longer force-loaded on every site — it is now
included only when a page actually uses holo classes, via the existing CSS
feature detection. Pagination and table-of-contents active-state glow
animations now honor `prefers-reduced-motion`.
