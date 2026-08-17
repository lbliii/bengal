---
name: write-content
description: Author Bengal pages with documented frontmatter, MyST directives, and bengal new page. Use when adding or editing site content, writing Markdown, or creating a page in a section.
---

# Write Bengal Content

Author pages as a **site author**. Claim only frontmatter fields and MyST
directives documented in
[/docs/build-sites/write/](https://lbliii.github.io/bengal/docs/build-sites/write/)
and
[/docs/reference/directives/](https://lbliii.github.io/bengal/docs/reference/directives/).
Do not invent directives or CLI flags.

Run these commands from the site root (the directory that contains `content/`).

## Create a page

```bash
bengal new page --help
```

`--name` is required. `--section` is optional (directory under `content/`).

```bash
bengal new page --name getting-started --section docs
bengal new page --name about
```

That writes a Markdown file with `title` and `date` frontmatter. Edit the file;
do not recreate it if it already exists.

## Frontmatter

Documented in
[/docs/build-sites/structure/organization/frontmatter/](https://lbliii.github.io/bengal/docs/build-sites/structure/organization/frontmatter/).
`title` is required.

```markdown
---
title: Getting Started
description: Install and run the product
date: '2026-08-17'
draft: false
weight: 10
type: doc
tags: [getting-started]
---

# Getting Started

Your content here.
```

**Common documented fields:** `description`, `date`, `draft`, `weight`, `slug`,
`url`, `aliases`, `lang`, `tags`, `category`, `keywords`, `author` / `authors`,
`type`, `variant`, `template`, `nav_title`, `canonical`, `noindex`, `og_image`,
`og_type`, `menu`, `parent`, `cascade`, `outputs`, `resources`.

- `draft: true` excludes the page from production builds. Preview drafts with
  `bengal serve --drafts` or `bengal build --drafts`.
- `type` examples from docs: `doc`, `blog`, `page`. Sections can set `type` (or
  `cascade.type`) on `_index.md`.
- Unknown fields become custom props (`page.props`). Do not invent Bengal
  reserved names.

**TODO:** If a field is not in the frontmatter reference, do not add it as if it
were built-in.

## Sections

A section is a directory under `content/` with `_index.md`:

```markdown
---
title: Guides
type: doc
---

# Guides
```

Directory names such as `blog`, `posts`, `docs`, and `guides` can infer a
content type; override with `type:` when needed. See
[/docs/build-sites/structure/organization/](https://lbliii.github.io/bengal/docs/build-sites/structure/organization/).

## Markdown and MyST

Write CommonMark. Directives use `:::{name}` (MyST). Nested blocks use named
closers (`:::{/name}`).

```markdown
:::{note}
Background that helps the reader.
:::

:::{warning}
Something to be careful about.
:::

:::{tip}
A practical suggestion.
:::
```

**Documented admonitions:** `note`, `tip`, `warning`, `caution`, `danger`,
`error`, `info`, `example`, `success`, `seealso`.

**Layout (from the directives reference):** `cards` / `grid`, `card`,
`child-cards`, `tab-set` / `tabs`, `tab-item` / `tab`, `dropdown` / `details`,
`container`, `steps`, `step`.

```markdown
:::{cards}
:columns: 2

:::{card} First
Short summary.
:::{/card}

:::{card} Second
Short summary.
:::{/card}
:::{/cards}
```

**Reuse:** `{include}` and `{literalinclude}` — see
[/docs/build-sites/write/reuse/](https://lbliii.github.io/bengal/docs/build-sites/write/reuse/).

**Links** (from the authoring guide):

```markdown
[External](https://example.com)
[Internal](/docs/get-started/)
[[docs/page]]
[[#heading]]
```

**Code:** fenced blocks with a language identifier. **Images:**
`![Alt](/images/file.png)` or `{figure}`. Full lists live in the directives
reference — do not invent a directive name.

## Preview

```bash
bengal serve
bengal build
```

## Docs to read

- [/docs/build-sites/write/authoring/](https://lbliii.github.io/bengal/docs/build-sites/write/authoring/)
- [/docs/reference/directives/](https://lbliii.github.io/bengal/docs/reference/directives/)
- [/docs/reference/directives/kitchen-sink/](https://lbliii.github.io/bengal/docs/reference/directives/kitchen-sink/)

## Checklist

- [ ] Page created with `bengal new page --name` (and `--section` if needed)
- [ ] Frontmatter `title` is set; other keys are from the frontmatter reference
- [ ] Directives are from the directives reference
- [ ] `bengal serve` or `bengal build` shows the page
