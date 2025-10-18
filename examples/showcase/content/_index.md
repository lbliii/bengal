---
title: "Bengal SSG - Complete Showcase"
description: "A comprehensive demonstration of all Bengal SSG features, template functions, and capabilities"
date: 2025-10-04
template: home.html

cta_buttons:
  - text: "Get Started"
    url: "docs/getting-started/quick-start.md"
    style: "primary"
  - text: "View Kitchen Sink"
    url: "docs/markdown/kitchen-sink.md"
    style: "secondary"

features:
  - icon: "⚡"
    title: "Blazing Fast"
    description: "Build 1000 pages in 2.8s. Incremental builds 18-42x faster than full rebuilds. Competitive with Hugo and 11ty."
    link:
      text: "See benchmarks"
      url: "#performance-benchmarks"

  - icon: "🎯"
    title: "Feature Complete"
    description: "75+ template functions, 9 admonition types, tabs, dropdowns, code highlighting, and comprehensive health checks."
    link:
      text: "View all features"
      url: "docs/markdown/kitchen-sink"

  - icon: "🤖"
    title: "LLM-Friendly"
    description: "First SSG with native AI support. Generate clean plain-text outputs perfect for training, RAG systems, and custom GPTs."
    link:
      text: "Learn more"
      url: "docs/output/output-formats"

  - icon: "✅"
    title: "Quality Assurance"
    description: "9 comprehensive health check validators ensure production-ready output with link validation and cache integrity."
    link:
      text: "Explore health checks"
      url: "docs/quality/health-checks"

  - icon: "🔄"
    title: "Incremental Builds"
    description: "Smart dependency tracking rebuilds only what changed. Change 1 page, rebuild in 0.067s instead of 2.8s."
    link:
      text: "View details"
      url: "#incremental-builds"

  - icon: "🧩"
    title: "Python Ecosystem"
    description: "Easy to extend with Python's rich libraries. Familiar Jinja2 templates and straightforward customization."
    link:
      text: "Get started"
      url: "docs/getting-started/installation"

quick_links:
  - icon: "📚"
    title: "Documentation"
    description: "Complete guides for all Bengal features"
    url: "docs/"

  - icon: "🌟"
    title: "Kitchen Sink"
    description: "See ALL features in one page"
    url: "docs/markdown/kitchen-sink"

  - icon: "🔧"
    title: "Template Functions"
    description: "75+ functions documented"
    url: "docs/templates/function-reference/"

  - icon: "🚀"
    title: "Quick Start"
    description: "Build your first site"
    url: "docs/getting-started/quick-start"

  - icon: "📖"
    title: "Hugo Migration"
    description: "Coming from Hugo? Start here"
    url: "tutorials/migration/from-hugo"

  - icon: "✅"
    title: "Health Checks"
    description: "Quality assurance tools"
    url: "docs/quality/health-checks"

stats:
  - value: "75+"
    label: "Template Functions"

  - value: "0.3s"
    label: "Build 100 Pages"

  - value: "42x"
    label: "Faster Incremental"

  - value: "9"
    label: "Health Validators"
---

# Bengal SSG - Complete Showcase

Welcome to the **comprehensive Bengal SSG showcase**! This site demonstrates every feature, directive, template function, and capability that Bengal offers.

---

## What is Bengal?

Bengal is a fast, Python-based static site generator.

**Key features:**

- Fast builds (2.8s for 1000 pages)
- 18-42x faster incremental builds
- 75+ template functions
- Health checks for production sites
- Output formats: HTML, JSON, LLM-txt

## Installation

```bash
pip install bengal
```

## Quick Start

```bash
# Create a new site
bengal new site my-site
cd my-site

# Start dev server
bengal site serve
```
