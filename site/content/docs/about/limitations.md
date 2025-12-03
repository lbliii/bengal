---
title: Limitations
description: What Bengal doesn't do and known constraints
weight: 25
type: doc
tags: [limitations, constraints, scope]
---

# Limitations

Bengal is opinionated software. Here's what it doesn't do, what it can't do yet, and what it will never do.

Being clear about limitations helps you choose the right tool and set realistic expectations.

---

## By Design (Intentional Scope)

These are deliberate choices, not missing features.

### No Server-Side Rendering

Bengal generates static HTML at build time. There's no runtime server processing requests.

**Implication**:
- No per-request dynamic content
- No server-side authentication
- No personalization based on user state

**Workarounds**:
- Client-side JavaScript for interactivity
- Edge functions (Netlify, Vercel, Cloudflare)
- Backend API for dynamic features
- Static generation with client-side hydration

**If you need SSR**: Use Next.js, Nuxt, Astro (SSR mode), or SvelteKit.

---

### No Built-in Image Optimization

Bengal doesn't resize, compress, convert, or generate responsive images automatically.

**Implication**:
- You must optimize images before adding them to your site
- No automatic WebP/AVIF conversion
- No responsive `srcset` generation

**Workarounds**:
- Pre-process with `sharp`, `imagemin`, or `squoosh`
- Use a CDN with image optimization (Cloudflare, Imgix, Cloudinary)
- Add a build step with `@11ty/eleventy-img` or similar

**Why?**: Image optimization is complex, opinionated, and better handled by dedicated tools. We don't want to ship a mediocre solution.

---

### No i18n/Multilingual Support (Yet)

Bengal doesn't have built-in support for multiple languages.

**Implication**:
- No automatic URL prefixes (`/en/`, `/fr/`)
- No language switcher component
- No translated content management
- No hreflang generation

**Workarounds**:
- Manual folder structure (`content/en/`, `content/fr/`)
- Separate sites per language
- Custom template logic for language switching

**Status**: Planned for v0.3.0. Tracking in [RFC: Internationalization](#).

---

### No JavaScript Framework SSR

Bengal doesn't server-render React, Vue, Svelte, or other JavaScript framework components.

**Implication**:
- JS frameworks run client-side only
- No hydration from server-rendered markup
- No Next.js-style component model

**You can still**:
- Include compiled JS bundles
- Use "islands" architecture (static HTML + interactive components)
- Embed client-side widgets

**If you need framework SSR**: Use Next.js, Nuxt, Astro, or SvelteKit.

---

### No Plugin System (Yet)

Bengal doesn't have a formal plugin architecture for extending core functionality.

**Implication**:
- Can't add custom content types via plugins
- Can't hook into build lifecycle
- Extensions require modifying Bengal source

**You can**:
- Add custom Jinja2 filters and functions
- Create custom templates and partials
- Use shortcodes for content extensions
- Pre/post-process with external scripts

**Status**: Plugin architecture planned for v0.4.0.

---

## Current Constraints (May Improve)

These are current limitations that may be addressed in future versions.

### GIL Limits Parallelism (Python < 3.14)

Python's Global Interpreter Lock limits true parallel execution on older Python versions.

**Implication**:
- Multi-threaded builds don't achieve full CPU utilization
- Slower than compiled alternatives at scale

**Mitigation**:
- Use Python 3.14+ with `PYTHON_GIL=0` for free-threading (1.8-2x faster)
- Enable `--fast` mode for optimized parallel execution
- Incremental builds eliminate most full-build pain

---

### Large Sites (> 5,000 Pages)

Full builds for very large sites can take 15-30+ seconds.

**Implication**:
- Initial builds feel slow
- CI/CD pipelines take longer
- Memory usage increases

**Mitigation**:
- Incremental builds (~40ms) handle most development workflows
- Use `--fast` and `PYTHON_GIL=0`
- Consider Hugo for 10,000+ page sites

**For context**: Most blogs have < 500 pages. Most documentation sites have < 2,000 pages. You're probably fine.

---

### Windows Support

Bengal is developed and tested primarily on macOS and Linux.

**Implication**:
- Windows may have path handling issues
- Some file watching features may behave differently
- Performance may vary

**Status**: We accept Windows bug reports and PRs, but don't actively test on Windows.

---

### Template Error Messages

Jinja2 error messages can be cryptic, especially for template inheritance issues.

**Implication**:
- Debugging template errors can be frustrating
- Line numbers may not match source files
- Stack traces can be long and confusing

**Mitigation**:
- Use `bengal utils theme debug` for template resolution issues
- Check the [Troubleshooting Guide](/docs/guides/troubleshooting/)
- Run with `--dev` profile for verbose output

---

## What We're Not Building

These are intentional scope boundaries. We won't add these features.

### No CMS/GUI

Bengal is code-first. There's no visual editor, admin panel, or GUI for content management.

**Why?**:
- GUIs add complexity and maintenance burden
- Developers prefer code and version control
- Many excellent headless CMS options exist (if you need one)

**If you need a CMS**: Pair Bengal with Decap CMS, Tina, Sanity, or Contentful.

---

### No Database Backend

Bengal is static-only. There's no database, no ORM, no dynamic data storage.

**Why?**:
- Static sites are simpler, faster, and more secure
- Databases add hosting complexity and cost
- Most content doesn't need real-time updates

**For dynamic data**: Use client-side fetching to APIs, or build with Next.js/Nuxt.

---

### No Hosting Platform

Bengal is a build tool. We don't host sites or provide deployment infrastructure.

**Why?**:
- Excellent hosting options already exist (Netlify, Vercel, Cloudflare, GitHub Pages)
- Hosting is a different business with different concerns
- Static sites work anywhere

---

### No WordPress Replacement

Bengal is for developers who write Markdown in text editors. It's not a WordPress alternative for non-technical users.

**If your users**:
- Don't know Git → Use WordPress, Ghost, or Squarespace
- Don't write Markdown → Use a CMS with visual editing
- Need WYSIWYG → Pair Bengal with Decap CMS or similar

---

## Comparison Summary

| Capability | Bengal | Needs External Tool |
|------------|--------|---------------------|
| Static HTML generation | ✅ | — |
| Markdown to HTML | ✅ | — |
| Template system | ✅ | — |
| Asset fingerprinting | ✅ | — |
| Dev server with live reload | ✅ | — |
| Image optimization | ❌ | sharp, Cloudinary, etc. |
| SSR/dynamic content | ❌ | Next.js, Nuxt, etc. |
| Multilingual | ❌ (planned) | Manual setup |
| Visual CMS | ❌ | Decap, Tina, etc. |
| Hosting | ❌ | Netlify, Vercel, etc. |

---

## See Also

- [Comparison with Other SSGs](/docs/about/comparison/)
- [Performance Benchmarks](/docs/about/benchmarks/)
- [FAQ](/docs/about/faq/)

