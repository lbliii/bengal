Retire the public `bengal.Page` and `bengal.core.Page` compatibility re-exports
plus the `Page.create_virtual()` compatibility constructor, and reduce internal
concrete `Page` coupling by routing page construction through page-like records
and the remaining SourcePage adapter boundary. Discovery now resolves i18n
metadata before creating `SourcePage` records instead of mutating adapted pages
afterward.
