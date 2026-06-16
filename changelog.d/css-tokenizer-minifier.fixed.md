Fixed the CSS minifier gluing `@scope (...) to (...)` into `to(...)`, which made
the parser treat `to` as a function and silently drop the scoped rule (#510). The
minifier is now a proper CSS Syntax Level 3 engine (`bengal.css`): it tokenizes
before serializing, so an identifier followed by whitespace and `(` can never
collapse into a function token. The old `bengal.assets.css_minifier.minify_css`
entry point is preserved as a thin re-export.

Correctness is enforced at runtime: after minifying, the engine re-parses its own
output and compares an independent meaning signature (selector descendant
combinators, declaration values, and — at the aggressive level — the resolved
cascade) against the input, returning the input unchanged on any mismatch. It can
therefore never emit corrupted CSS.

`minify_css` also gained an optional `level` argument: `"safe"` (default, lossless
whitespace/comment removal), `"optimize"` (adds color/number normalization), and
`"aggressive"` (adds cascade-invariant structural rewrites such as empty-rule
removal, exact-duplicate dedup, and adjacent-rule merging). The default build path
is unchanged.
