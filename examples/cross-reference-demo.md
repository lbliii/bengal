---
title: Cross-Reference Examples
id: xref-demo
---

# Cross-Reference Examples

This page demonstrates Bengal's three cross-reference methods.

## 1. Path References (Most Common)

Link to pages by their file path:

- [[docs/installation]]
- [[docs/installation|Custom Text]]

## 2. Heading References

Link to sections:

- [[#path-references-most-common]]  (this section)
- [[#heading-references]]  (next section)

## 3. Custom ID References

This page has `id: xref-demo` in frontmatter.

Reference it from anywhere:
- [[id:xref-demo]]
- [[id:xref-demo|Demo Page]]

## Test It

Try creating another page that links here:

```markdown
---
title: My New Page
---

Check out the [[id:xref-demo]] for examples!
```
