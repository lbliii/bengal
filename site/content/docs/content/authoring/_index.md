---
title: Content Authoring
description: Writing rich content with Markdown and MyST
weight: 20
draft: false
lang: en
tags: [authoring, markdown, myst]
keywords: [markdown, myst, directives, shortcodes, writing]
category: guide
---

# Content Authoring

Writing rich content in Bengal with Markdown, MyST directives, and shortcodes.

## Markdown Basics

Bengal uses standard CommonMark Markdown with MyST (Markedly Structured Text) extensions.

### Text Formatting

```markdown
**bold text**
*italic text*
~~strikethrough~~
`inline code`
```

### Links and Images

```markdown
[Link text](https://example.com)
[Internal link](/docs/getting-started/)

![Alt text](/images/hero.jpg)
![With title](/images/hero.jpg "Image title")
```

### Code Blocks

````markdown
```python
def hello():
    print("Hello, Bengal!")
```
````

With line highlighting:

````markdown
```python {hl_lines="2"}
def hello():
    print("Hello, Bengal!")  # This line highlighted
```
````

## MyST Directives

MyST extends Markdown with powerful directives for rich content.

### Admonitions

```markdown
:::{note}
This is a note admonition.
:::

:::{warning}
This is a warning!
:::

:::{tip}
Pro tip: Use directives for callouts.
:::
```

### Tabs

```markdown
::::{tab-set}
:::{tab-item} Python
```python
print("Hello")
```
:::
:::{tab-item} JavaScript
```javascript
console.log("Hello");
```
:::
::::
```

## In This Section

- **[Directives Reference](/docs/content/authoring/directives/)** — All available MyST directives
- **[Shortcodes](/docs/content/authoring/shortcodes/)** — Using and creating shortcodes


