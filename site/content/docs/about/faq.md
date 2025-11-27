---
title: Frequently Asked Questions
description: Answers to common questions about Bengal's features, limitations, and compatibility.
weight: 20
type: doc
tags: [faq, help, support]
---

# FAQ

## General

:::{dropdown} Is Bengal free?
**Yes!** Bengal is open-source software released under the MIT License. You can use it for personal and commercial projects for free.
:::

:::{dropdown} What Python version does Bengal require?
**Python 3.14 or later** (3.14t free-threaded build recommended for best performance).

See the [Installation Guide](/docs/getting-started/installation/) for why and how to set it up.
:::

## Technical

:::{dropdown} Can I use React/Vue/Svelte?
**Yes, but...** Bengal is a Static Site Generator that outputs HTML. You can absolutely include compiled JS bundles (like React components) in your pages, but Bengal does not do server-side rendering (SSR) for JS frameworks.

Use Bengal for the content structure and React for "Islands of Interactivity."
:::

:::{dropdown} How do I host a Bengal site?
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
**Yes.** Bengal supports standard Markdown (CommonMark). We also support GitHub Flavored Markdown (GFM) tables and task lists out of the box.
:::

:::{dropdown} How do I add a new theme?
You can install themes via `pip` or clone them into your `themes/` directory.
See the [Themer Quickstart](/docs/getting-started/themer-quickstart/) for details.
:::
