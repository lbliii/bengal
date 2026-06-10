Theme-library provider resolution is now cached per `(site_root, theme_chain)`.
`resolve_theme_providers()` was previously called on two independent build paths
with no shared state — asset discovery and Kida engine loader/filter setup — and,
under the #350 shard-parallel render backend, once per worker-thread pipeline.
Each call did `importlib.import_module` plus convention-hook probing
(`get_library_contract` / `get_loader` / `static_path` / `register_filters`) for
every declared library, rebuilding the contract strictly more than twice per
build. A module-level `LRUCache` (RLock-backed, free-threading-safe under CPython
3.14t) now collapses all of these to a single resolution that every caller and
shard thread shares; the resolved tuple of frozen+slots providers is read-only
and safe to share. The cache is registered with the central cache registry
(invalidated on full rebuild / config change / build start) so theme.toml
`libraries` edits in long-lived dev-server/incremental processes re-resolve.
The default-theme happy path is unchanged: a theme that declares no libraries
caches the empty tuple `()` and short-circuits identically, keeping output
byte-identical (verified against baseline on the default-theme path). See #365.
