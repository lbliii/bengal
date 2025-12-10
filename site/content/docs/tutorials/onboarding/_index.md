---
title: Coming From Another Tool?
description: Onboarding guides for users migrating from Sphinx, Hugo, Docusaurus,
  and other documentation tools
weight: 15
tags:
- tutorial
- migration
- onboarding
keywords:
- sphinx
- hugo
- docusaurus
- mdx
- rst
- migration
- onboarding
icon: boomerang
---
# Coming From Another Tool?

Choose the guide that matches your background:

:::{cards}
:columns: 3

:::{card} From Sphinx/RST
:icon: 📜
:link: from-sphinx

You know RST directives, `.. note::`, and `conf.py`. Bengal's MyST syntax will feel familiar.
:::

:::{card} From Hugo
:icon: ⚡
:link: from-hugo

You use Hugo shortcodes like `{{</* highlight */>}}` and Go templates. Bengal directives work similarly.
:::

:::{card} From Docusaurus/MDX
:icon: ⚛️
:link: from-docusaurus

You write MDX with React components like `<Tabs>`. Bengal offers the same features without JSX.
:::

:::{/cards}

## Quick Comparison

| Feature | Sphinx/RST | Hugo | Docusaurus | **Bengal** |
|---------|------------|------|------------|------------|
| Callouts | `.. note::` | `{{</* notice */>}}` | `:::note` | `:::{note}` |
| Tabs | Extension | `{{</* tabs */>}}` | `<Tabs>` | `:::{tab-set}` |
| Code inclusion | `.. literalinclude::` | `readFile` | Import | `:::{literalinclude}` |
| Config format | `conf.py` | `config.toml` | `docusaurus.config.js` | `bengal.toml` |
| Template engine | Jinja2 | Go templates | React | Jinja2 |

## Common Ground

All guides assume you're comfortable with:

- Markdown basics
- YAML frontmatter
- Command-line tools
- File-based content organization

## What Makes Bengal Different

:::{tip} Key Insight
Bengal combines the **structured directive syntax** of Sphinx, the **file-based simplicity** of Hugo, and the **rich components** of Docusaurus—all in pure Markdown without compilation steps or framework lock-in.
:::

Choose your guide above to see specific feature mappings and examples.
