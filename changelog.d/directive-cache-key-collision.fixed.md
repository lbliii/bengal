Fixed a directive render-cache key collision in the Patitas backend. The
structural fingerprint only recursed through `block.children` and probed a
hand-picked attribute list, so directives whose bodies were lists, tables, or
fenced code (which patitas stores in `.items`/`.head`/`.body` and source
offsets) collapsed onto one cache key — the first render's HTML was then served
for all later ones. On versioned sites (where the directive cache is enabled)
this could render stale, duplicated directive output. The key now walks every
declared slot across each node's MRO, so distinct directives can no longer
collide.
