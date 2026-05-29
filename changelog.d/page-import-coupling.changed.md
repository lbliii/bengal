Retire the public `bengal.Page` and `bengal.core.Page` compatibility re-exports
and reduce internal concrete `Page` coupling by routing page construction
through page-like records and the remaining SourcePage adapter boundary.
