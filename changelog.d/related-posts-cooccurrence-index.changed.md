Related-posts computation is dramatically faster on large sites. The candidate
filters (skip generated/home/section-index pages) and the deterministic
tie-break key are now computed once per build instead of for every
(page × tag × candidate) in the scoring loop. On a 4,288-page site this cut the
related-posts phase from ~24s to ~3s (~8×) with byte-identical output. See #350.
