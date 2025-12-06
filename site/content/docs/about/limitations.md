---
title: Limitations
description: What Bengal doesn't do—and when to use something else
weight: 25
type: doc
tags: [limitations, constraints, scope]
---

# Limitations

Bengal is opinionated software. Here's what it doesn't do, what it can't do yet, and what it will never do.

Being clear about limitations helps you choose the right tool and set realistic expectations. We want you to be happy, even if it means using another tool.

---

## When to Use Something Else

### Large Sites (10,000+ Pages)

Sites with 10,000+ pages will feel the Python GIL. For massive sites, Hugo's raw speed wins.

**The numbers:**
- Bengal: ~200 pages/sec (parallel, with free-threading)
- Hugo: ~10,000+ pages/sec

**For sites under 5,000 pages**, Bengal's developer experience and incremental builds make the difference negligible in practice.

**If you have 50,000+ pages**: Use [Hugo](https://gohugo.io). No hard feelings.

---

### React/Vue SPAs

Bengal generates static HTML. It doesn't server-render JavaScript framework components.

**Bengal is for:** Multi-Page Apps (MPA) where static generation makes sense.

**If you need:**
- React/Vue/Svelte components with SSR
- Client-side routing
- App-like experiences

**Use:** [Next.js](https://nextjs.org), [Nuxt](https://nuxt.com), or [Astro](https://astro.build).

---

### Non-Technical Users

Bengal is code-first. There's no visual editor, admin panel, or WYSIWYG interface.

**If your users:**
- Don't know Git → Use WordPress, Ghost, or Squarespace
- Don't write Markdown → Use a CMS with visual editing
- Need WYSIWYG → Pair Bengal with [Decap CMS](https://decapcms.org) or similar

---

## By Design (Intentional Scope)

These are deliberate choices, not missing features.

### No Server-Side Rendering

Bengal generates static HTML at build time. There's no runtime server processing requests.

**What this means:**
- No per-request dynamic content
- No server-side authentication
- No personalization based on user state

**Workarounds:**
- Client-side JavaScript for interactivity
- Edge functions (Netlify, Vercel, Cloudflare)
- Backend APIs for dynamic features

---

### No Built-in Image Optimization

Bengal doesn't resize, compress, or convert images automatically.

**Why?** Image optimization is complex and opinionated. Dedicated tools do it better.

**Use instead:**
- Pre-process with `sharp`, `imagemin`, or `squoosh`
- CDN with optimization (Cloudflare, Imgix, Cloudinary)
- Build step with `@11ty/eleventy-img`

---

### No JavaScript Framework SSR

Bengal doesn't server-render React, Vue, or Svelte components.

**You can still:**
- Include compiled JS bundles
- Use "islands" architecture (static HTML + interactive components)
- Embed client-side widgets

---

## Current Constraints (May Improve)

### No i18n Support (Yet)

Bengal doesn't have built-in multilingual support.

**Workarounds:**
- Manual folder structure (`content/en/`, `content/fr/`)
- Separate sites per language
- Custom template logic

**Status:** Planned for v0.3.0.

---

### No Formal Plugin System (Yet)

Extensions require modifying Bengal source or using Jinja2 customization points.

**You can:**
- Add custom Jinja2 filters and functions
- Create custom templates and partials
- Use shortcodes for content extensions

**Status:** Plugin architecture planned for v0.4.0.

---

### Windows Support

Bengal is developed primarily on macOS and Linux. Windows may have edge cases.

**Status:** We accept Windows bug reports and PRs but don't actively test on Windows.

---

## What We're Not Building

### No CMS/GUI

Bengal is code-first. No admin panel, no visual editor.

**If you need a CMS:** Pair Bengal with Decap CMS, Tina, Sanity, or Contentful.

---

### No Database Backend

Bengal is static-only. No database, no ORM.

**For dynamic data:** Use client-side fetching to APIs, or build with Next.js/Nuxt.

---

### No Hosting Platform

Bengal is a build tool. We don't host sites.

**Deploy to:** Netlify, Vercel, Cloudflare Pages, GitHub Pages, or any static host.

---

## Quick Reference

| Capability | Bengal | Alternative |
|------------|--------|-------------|
| Static HTML | ✅ | — |
| Incremental builds | ✅ | — |
| Large sites (50k+) | ⚠️ Slow | Hugo |
| SSR/dynamic | ❌ | Next.js, Nuxt |
| Image optimization | ❌ | sharp, Cloudinary |
| Multilingual | ❌ (planned) | Manual setup |
| Visual CMS | ❌ | Decap, Tina |

---

## See Also

- [Choosing the Right SSG](/docs/about/comparison/)
- [Performance Benchmarks](/docs/about/benchmarks/)
- [FAQ](/docs/about/faq/)
