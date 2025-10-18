---
title: Extended Markdown
description: Advanced markdown features including tables, footnotes, and task lists
type: doc
weight: 3
tags: ["markdown", "advanced", "gfm"]
toc: true
---

# Extended Markdown

**Purpose**: Learn advanced markdown features beyond the basics for richer content.

## What You'll Learn

- Create tables for structured data
- Use task lists for checklists
- Add footnotes for references
- Format definition lists
- Use strikethrough and other GFM features

## Tables

Create tables with pipes `|` and hyphens `-`:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Row 1    | Data     | More data |
| Row 2    | Data     | More data |
| Row 3    | Data     | More data |
```

**Result:**

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Row 1    | Data     | More data |
| Row 2    | Data     | More data |
| Row 3    | Data     | More data |

### Column Alignment

Use colons `:` to align columns:

```markdown
| Left Aligned | Center Aligned | Right Aligned |
|:-------------|:--------------:|--------------:|
| Left         | Center         | Right         |
| Text         | Text           | Text          |
```

**Result:**

| Left Aligned | Center Aligned | Right Aligned |
|:-------------|:--------------:|--------------:|
| Left         | Center         | Right         |
| Text         | Text           | Text          |

### Table Tips

```{tip} Table Best Practices
- Keep tables simple - complex data might need a different format
- Use alignment for numbers (right) and text (left)
- Consider breaking very wide tables into multiple tables
- Test readability on mobile devices
```

### Common Table Patterns

**Command reference:**

```markdown
| Command | Description | Example |
|---------|-------------|---------|
| `build` | Build the site | `bengal build` |
| `serve` | Start dev server | `bengal serve` |
| `clean` | Clean output | `bengal clean` |
```

**Result:**

| Command | Description | Example |
|---------|-------------|---------|
| `build` | Build the site | `bengal build` |
| `serve` | Start dev server | `bengal serve` |
| `clean` | Clean output | `bengal clean` |

**Comparison table:**

```markdown
| Feature | Free | Pro |
|---------|:----:|:---:|
| Pages | 10 | ∞ |
| Support | Email | 24/7 |
| Price | $0 | $99 |
```

## Task Lists

Create checklists with `- [ ]` and `- [x]`:

```markdown
## Project Tasks

- [x] Set up Bengal site
- [x] Create initial pages
- [ ] Write blog posts
- [ ] Add images
- [ ] Deploy to production
```

**Result:**

## Project Tasks

- [x] Set up Bengal site
- [x] Create initial pages
- [ ] Write blog posts
- [ ] Add images
- [ ] Deploy to production

Use task lists for:
- Checklists and to-do lists
- Requirements tracking
- Tutorial progress indicators
- Feature checklists

## Footnotes

Add footnotes for references and additional information:

```markdown
Bengal is a static site generator[^1] written in Python[^2].

[^1]: Static site generators create HTML files at build time, not runtime.
[^2]: Python is a popular programming language known for readability.
```

**Result:**

Bengal is a static site generator[^1] written in Python[^2].

[^1]: Static site generators create HTML files at build time, not runtime.
[^2]: Python is a popular programming language known for readability.

### Footnote Tips

- Footnotes appear at the bottom of the page automatically
- Numbers are auto-generated and reordered
- You can use descriptive identifiers: `[^my-note]`
- Footnote content can be multi-paragraph

## Strikethrough

Strike through text with `~~`:

```markdown
~~This text is crossed out~~

Price: ~~$99~~ $49 (50% off!)
```

**Result:**

~~This text is crossed out~~

Price: ~~$99~~ $49 (50% off!)

## Definition Lists

Create glossaries and term definitions:

```markdown
Term 1
: Definition of term 1

Term 2
: First definition of term 2
: Second definition of term 2

Complex Term
: Definition paragraph with **bold** and *italic*.
: Another aspect of the definition.
```

**Result:**

Term 1
: Definition of term 1

Term 2
: First definition of term 2
: Second definition of term 2

## Auto-Linking URLs

URLs automatically become links:

```markdown
Visit https://bengal-ssg.org for more info.

Email us at support@example.com
```

**Result:**

Visit https://bengal-ssg.org for more info.

```{warning} Link Best Practices
While auto-linking works, prefer explicit links with descriptive text for better accessibility:

❌ `Visit https://bengal-ssg.org`  
✅ `Visit the [Bengal website](https://bengal-ssg.org)`
```

## Emoji

Use emoji in your content:

```markdown
:tada: :rocket: :heart: :star: :bulb:

Congratulations! 🎉
```

**Result:** :tada: :rocket: :heart: :star: :bulb:

Common emoji:
- 📝 `:memo:` - Documentation
- ✅ `:white_check_mark:` - Completed
- ⚠️ `:warning:` - Warning
- 🐛 `:bug:` - Bug
- 🚀 `:rocket:` - Launch/Release

## Subscript and Superscript

For mathematical and scientific notation:

```markdown
H~2~O (subscript)

E = mc^2^ (superscript)
```

```{note}
Support for subscript/superscript may vary by markdown parser. Test in your build.
```

## Practical Examples

### Tutorial Checklist

```markdown
## Setup Checklist

Complete these steps:

- [x] Install Python 3.8+
- [x] Install Bengal: `pip install bengal`
- [ ] Create site: `bengal new site mysite`
- [ ] Configure in `bengal.toml`
- [ ] Build: `bengal build`

**Next:** See the [configuration guide](../advanced/navigation.md).
```

### API Documentation

```markdown
## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `title` | string | required | Site title |
| `baseurl` | string | `/` | Base URL path |
| `theme` | string | `default` | Theme name |
| `parallel` | boolean | `true` | Enable parallel builds[^perf] |

[^perf]: Parallel builds use multiple CPU cores for faster builds.
```

### Changelog Entry

```markdown
## Version 0.2.0

### Added
- ✨ New directive system
- 🚀 Parallel asset processing

### Changed
- ~~Synchronous~~ Asynchronous file operations

### Fixed
- 🐛 Fixed navigation bug (#123)
```

### Glossary

```markdown
## Glossary

Static Site Generator (SSG)
: A tool that generates static HTML files from templates and content at build time.

Frontmatter
: Metadata at the top of markdown files, typically in YAML format.

Directive
: Special syntax for rich content like callouts, tabs, and cards.
```

## Feature Comparison

| Feature | Basic Markdown | Extended Markdown |
|---------|:--------------:|:-----------------:|
| Headings | ✅ | ✅ |
| Lists | ✅ | ✅ |
| Links | ✅ | ✅ |
| Tables | ❌ | ✅ |
| Task lists | ❌ | ✅ |
| Footnotes | ❌ | ✅ |
| Strikethrough | ❌ | ✅ |
| Definition lists | ❌ | ✅ |

## Next Steps

You've mastered extended markdown! Now explore:

- **[Directives](../directives/)** - Rich content with callouts, tabs, and cards
- **[Variables](../advanced/variables.md)** - Dynamic content with variable substitution
- **[Content Types](../content-types/)** - Different layouts for different content
- **[Kitchen Sink](../kitchen-sink.md)** - See everything in action

## Related

- [Markdown Basics](markdown-basics.md) - Essential syntax
- [Tables](../directives/cards.md) - Alternative to tables with card grids
- [Internal Links](internal-links.md) - Cross-referencing pages
