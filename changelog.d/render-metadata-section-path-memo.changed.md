Per-page rendering is faster: `RuntimePage.metadata` is read hundreds of times per
page, and each read previously recomputed the section path relative to `content/`
via `Path.relative_to` before consulting its cache. The relative section path now is
memoized per site (invalidated when the section changes), eliminating ~265k
`Path.relative_to`/`pathlib` calls on a 300-page docs build and cutting single-thread
render time ~27% (13.4 → 9.7 ms/page, median of 5 sequential builds). Output is
byte-identical (verified by a timestamp-normalized full-tree comparison: HTML trees
hash-equal before/after).
