### Fixed

- **output**: `graph/graph.json` and the search `index.json` are now byte-identical
  across rebuilds of unchanged content. Knowledge-graph node ids previously used a
  per-process randomized hash (and an absolute path), graph edges came out in a
  process-dependent order, and equally-weighted tags were ordered nondeterministically
  — so two builds of the same site produced diffing output. IDs are now a stable hash
  of the site-relative path, edges and tags sort deterministically.
