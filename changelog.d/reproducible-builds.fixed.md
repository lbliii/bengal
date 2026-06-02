Builds are now byte-reproducible: identical content produces identical output
across repeated builds and across worker counts. Three sources of
thread/hash-dependent output were eliminated — related-posts now break score ties
by a stable key, tag listings sort ties deterministically, and tag accent colors
use a stable digest instead of Python's per-process-randomized `hash()`. This makes
parallel (free-threaded) output trustworthy for caching, CDNs, and version control.
