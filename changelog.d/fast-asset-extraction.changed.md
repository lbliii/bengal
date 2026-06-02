Render-time asset-dependency extraction now uses a fast single-pass scanner instead
of the stdlib `HTMLParser`, cutting per-page extraction ~4x (4.84 → 1.19 ms/page)
with a byte-identical dependency set (verified by an adversarial parity suite). The
post-render asset audit also memoizes existence checks. Benchmark docs were corrected
to committed baselines (the previous "256/373 pages/sec" figures were unbacked), and
the `gil_speedup` harness now reports a full per-phase ledger.
