---
title: Coming From Another Tool?
nav_title: Migrate
description: Onboarding guides for users migrating from Sphinx, Hugo, Docusaurus,
  MkDocs, Mintlify, Fern, and other documentation tools
weight: 15
tags:
- tutorial
- migration
- onboarding
keywords:
- sphinx
- hugo
- docusaurus
- mkdocs
- mintlify
- fern
- mdx
- rst
- migration
- onboarding
- api documentation
icon: boomerang
---

# Coming From Another Tool?

Choose the guide that matches your background:

:::{cards}
:columns: 3

:::{card} From Sphinx/RST
:icon: book
:link: from-sphinx

You know RST directives, `.. note::`, and `conf.py`. Bengal's MyST syntax will feel familiar.
:::{/card}

:::{card} From Hugo
:icon: zap
:link: from-hugo

You use Hugo shortcodes like `{{</* highlight */>}}` and Go templates. Bengal directives work similarly.
:::{/card}

:::{card} From Docusaurus/MDX
:icon: rocket
:link: from-docusaurus

You write MDX with React components like `<Tabs>`. Bengal offers the same features without JSX.
:::{/card}

:::{card} From MkDocs
:icon: file-text
:link: from-mkdocs

You use `!!! note` admonitions and `mkdocs.yml`. Bengal's Python-native approach will feel right at home.
:::{/card}

:::{card} From Mintlify
:icon: sparkle
:link: from-mintlify

You use Mintlify's hosted MDX with `<Card>` components. Get the same polish, self-hosted.
:::{/card}

:::{card} From Fern
:icon: code
:link: from-fern

You use Fern's API-first docs platform. Bengal gives you documentation freedom without SDK lock-in.
:::{/card}

:::{/cards}

## Quick Comparison

| Feature | Sphinx/RST | Hugo | Docusaurus | MkDocs | Mintlify | Fern | **Bengal** |
|---------|------------|------|------------|--------|----------|------|------------|
| Callouts | `.. note::` | `{{</* notice */>}}` | `:::note` | `!!! note` | `<Note>` | `<Callout>` | `:::{note}` |
| Tabs | Extension | `{{</* tabs */>}}` | `<Tabs>` | `=== "Tab"` | `<Tabs>` | `<CodeBlocks>` | `:::{tab-set}` |
| Cards | Extension | Shortcode | `<Card>` | Extension | `<CardGroup>` | `<Cards>` | `:::{cards}` |
| Config format | `conf.py` | `config.toml` | `.js` | `mkdocs.yml` | `mint.json` | `docs.yml` | `bengal.toml` |
| Template engine | Jinja2 | Go | React | Jinja2 | MDX | MDX | Jinja2 |
| Hosting | Self-host | Self-host | Self-host | Self-host | Managed | Managed | Self-host |

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
