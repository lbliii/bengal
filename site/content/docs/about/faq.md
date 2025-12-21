---
title: Frequently Asked Questions
nav_title: FAQ
description: Answers to common questions about Bengal's features, limitations, and
  compatibility.
weight: 20
type: doc
tags:
- faq
- help
- support
---

# FAQ

## General

:::{dropdown} Does Bengal guarantee backwards compatibility?
:icon: alert
**No.** Bengal prioritizes correctness and clarity over long-term compatibility.

Each release represents the best solution we know how to deliver. When existing behavior no longer reflects the best design, it may be changed or removed. Breaking changes produce clear error messages, not silent degradation.

**What this means for you:**

- Read release notes before upgrading
- Expect to make changes when upgrading major versions
- Pin your version if you need stability

See [[docs/about/philosophy|Project Philosophy]] for the full rationale.
:::

:::{dropdown} Is Bengal free?
:icon: star
**Yes!** Bengal is open-source software released under the MIT License. You can use it for personal and commercial projects for free.
:::

:::{dropdown} What Python version does Bengal require?
:icon: code
**Python 3.14 or later** (3.14t free-threaded build recommended for best performance).

See the [[docs/get-started/installation|Installation Guide]] for why and how to set it up.
:::

## Technical

:::{dropdown} Can I use React/Vue/Svelte?
:icon: settings
**Yes, but...** Bengal is a Static Site Generator that outputs HTML. You can absolutely include compiled JS bundles (like React components) in your pages, but Bengal does not do server-side rendering (SSR) for JS frameworks.

Use Bengal for the content structure and React for "Islands of Interactivity."
:::

:::{dropdown} How do I host a Bengal site?
:icon: upload
Since Bengal outputs static HTML/CSS/JS (in the `public/` folder), you can host it **anywhere**:
*   GitHub Pages
*   Netlify
*   Vercel
*   AWS S3
*   Apache/Nginx

No database or Python server is required for hosting.
:::

## Content & Theming

:::{dropdown} Can I use standard Markdown?
:icon: file
**Yes.** Bengal supports standard Markdown (CommonMark). We also support GitHub Flavored Markdown (GFM) tables and task lists out of the box.
:::

:::{dropdown} How do I add a new theme?
:icon: palette
You can install themes via `pip` or clone them into your `themes/` directory.
See the [[docs/get-started/quickstart-themer|Themer Quickstart]] for details.
:::
