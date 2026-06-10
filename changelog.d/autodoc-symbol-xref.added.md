Autodoc now cross-links symbol names to their documented pages (#327). A new
deterministic `SymbolResolver` service (`bengal/autodoc/symbol_resolver.py`) maps
qualified and simple symbol names to a real, page-aware URL: modules resolve to
their own page, while inline elements (classes, functions, methods rendered as
cards on a module page) resolve to that module page plus a stable `#Card` anchor,
so links never 404. Return types, parameter types, base classes, `See Also`
targets, and bare `Name` code spans in docstrings are linked when they resolve to
a documented symbol and degrade to plain text otherwise. Simple-name resolution is
ambiguity-safe — a name shared by two documented symbols resolves to neither (a
wrong link is worse than no link). The `See Also` section, previously dropped, now
renders on Python module and class output. xref runs at render time (via the
`xref_type` / `xref_docstring` template filters) so extraction and cache hashing
stay unchanged, and xref output is byte-identical across rebuilds.
