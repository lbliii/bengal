Fixed the CSS minifier gluing `@scope (...) to (...)` into `to(...)`, which made
the parser treat `to` as a function and silently drop the scoped rule (#510). The
minifier is now a proper CSS Syntax Level 3 engine (`bengal.css`): it tokenizes
before serializing, so an identifier followed by whitespace and `(` can never
collapse into a function token.

The legacy CSS code paths were removed so Bengal dogfoods the new engine
entirely: the `bengal.assets.css_minifier` shim and the regex-based
`bengal/core/asset/css_transforms.py` (`lossless_minify_css`,
`remove_duplicate_bare_h1_rules`, `transform_css_nesting`) are gone. Native CSS
nesting (`&:hover`) is now preserved rather than flattened (Baseline 2023);
import `minify_css` from `bengal.css`.

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
