# CommonMark 0.31 Intentional Deviations

**Status:** Current as of 2026-03-13  
**Spec:** [CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/)  
**Parser:** Patitas (used by Bengal)

## Summary

Patitas passes all 652 CommonMark 0.31.2 spec examples. The spec test suite (`patitas/tests/test_commonmark_spec.py`) applies normalization before comparison to account for intentional extensions and output style differences.

## Normalizations Applied (Test-Only)

These are **not** spec violations—they are output style choices that the test normalizer strips for comparison:

| Output | Patitas | Spec | Reason |
|--------|---------|------|--------|
| Heading IDs | `<h1 id="slug">` | `<h1>` | Bengal adds `id` for anchor links; normalized away in spec tests |
| Line break style | `<br />` | `<br>` | Both valid HTML5; normalized for comparison |

## Extensions (Beyond CommonMark)

Patitas and Bengal add features not in the CommonMark spec:

- **Directives** — MyST-style `:::{name}` blocks
- **Roles** — Inline `:role:` syntax
- **GFM tables** — GitHub Flavored Markdown tables
- **Footnotes** — `[^1]` syntax
- **Task lists** — `- [ ]` and `- [x]`
- **Math** — `$...$` and `$$...$$` (via plugin)

These do not affect CommonMark spec compliance.

## Verification

```bash
# From Patitas
pytest tests/test_commonmark_spec.py -m commonmark -v

# From Bengal (workspace)
poe test-commonmark
```
