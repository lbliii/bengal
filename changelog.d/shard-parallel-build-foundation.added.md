Lay the foundation for an experimental shard-parallel cold build (issue #350,
Phase 2; gated off by default, no change to the default build path): a
deterministic pre-parse content-file sharder, a from-live-page map step, and
shard-worker parse + render legs, so each worker can parse and render its own
~1/N of the corpus in its own heap (avoiding the copy-on-write tax that
regressed the Phase-1 fork-after-parse backend).
