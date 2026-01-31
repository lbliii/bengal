---
title: Limitations
description: What Bengal doesn't do
weight: 25
tags:
- limitations
- constraints
---

# Limitations

## No Server-Side Rendering

Bengal generates static HTML at build time. There's no runtime server for dynamic content.

For dynamic features, use client-side JavaScript or edge functions (Cloudflare Workers, Vercel Edge Functions, etc.).

## No Theme Browse UI

Bengal supports installing themes from PyPI (`bengal theme install bengal-theme-minimal`) and discovering installed themes (`bengal theme list`), but there's no built-in gallery to browse available themes. Check PyPI for packages prefixed with `bengal-theme-`.

## Large Sites

Sites with 10,000+ pages have slower full builds (~35s for 10K pages). Incremental builds remain fast (35-80ms for single-page edits) regardless of site size.

For very large sites:
- Use `--fast` mode for maximum performance
- Enable free-threading (`PYTHON_GIL=0`) for additional speedup
- Use `--memory-optimized` if RAM is constrained

## Windows

Developed primarily on macOS/Linux. Windows works but may have edge cases with path handling or file watching.

## No Automatic Responsive Image Generation at Build Time

Bengal provides image processing functions (`fill`, `fit`, `resize`, format conversion, srcset generation) that work in templates, but doesn't automatically generate responsive variants during the build phase. You call these functions explicitly in templates:

```kida
{# Generate srcset using the filter #}
<img src="{{ image_url('hero.jpg', width=800) }}"
     srcset="{{ 'hero.jpg' | image_srcset([400, 800, 1200]) }}"
     sizes="(max-width: 640px) 400px, 800px" />

{# Or use the global function with default sizes (400, 800, 1200, 1600) #}
<img srcset="{{ image_srcset_gen('hero.jpg') }}" sizes="100vw" />
```

For automatic build-time generation, pre-process images or use a CDN with on-the-fly resizing.

:::{seealso}
- [[docs/about/comparison|Key Capabilities]]
- [[docs/about/faq|FAQ]]
- [[docs/theming/templating/image-processing|Image Processing]]
:::
