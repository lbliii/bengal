---
title: Math and LaTeX
description: Inline and block mathematical expressions with LaTeX
weight: 45
tags:
- content
- markdown
- math
- latex
category: guide
icon: function
---

# Math and LaTeX

Bengal supports LaTeX-style mathematical expressions in Markdown. Enable the `content.math` theme feature to render equations with KaTeX.

## Syntax

### Inline Math

Use single dollar signs for inline equations:

```markdown
The equation $E = mc^2$ is famous. So is $\sum_{i=1}^n x_i$.
```

### Block Math

Use double dollar signs on separate lines for display equations:

```markdown
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$
```

### Role Syntax

Use the `{math}` role as an alternative:

```markdown
The equation {math}`E = mc^2` is famous.
```

## Enabling Math Rendering

Add `content.math` to your theme features in `config/_default/theme.yaml`:

```yaml
theme:
  features:
    - content.math
```

This loads KaTeX (~200KB) for client-side rendering. Omit the feature if your site does not use math.

## Escaping

- Use `\$` for a literal dollar sign in prose
- Inside code spans, `$` is literal and not parsed as math
