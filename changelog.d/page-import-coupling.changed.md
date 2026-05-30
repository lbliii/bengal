Retire the public `bengal.Page` and `bengal.core.Page` compatibility re-exports
plus the `Page.create_virtual()` compatibility constructor, and reduce internal
concrete `Page` coupling by routing page construction through page-like records
and the remaining SourcePage adapter boundary. Discovery now resolves i18n
metadata before creating `SourcePage` records instead of mutating adapted pages
afterward. Non-compatibility tests no longer use local `Page`-named doubles that
obscure the remaining production adapter/class boundary. The remaining adapter
now lazy-loads the legacy class so importing content discovery helpers does not
load `bengal.core.page`. Tests now import Page submodules directly and guard
against new package-root imports from `bengal.core.page`.
