---
title: Callouts & Admonitions
nav_title: Callouts
description: Draw attention to important information with notes, warnings, and tips
weight: 60
category: how-to
icon: info
---
# Callouts & Admonitions

How to highlight important information for your readers.

## Basic Callouts

Bengal supports MyST-style admonitions:

```markdown
:::{note}
This is helpful background information.
:::
```

:::{note}
This is helpful background information.
:::

## Callout Types

### Informational

```markdown
:::{note}
Background information that's good to know.
:::

:::{info}
Additional context or details.
:::
```

:::{note}
Background information that's good to know.
:::

### Helpful

```markdown
:::{tip}
A helpful suggestion or best practice.
:::
```

:::{tip}
A helpful suggestion or best practice.
:::

### Caution

```markdown
:::{warning}
Something to be careful about.
:::

:::{caution}
Proceed with care.
:::
```

:::{warning}
Something to be careful about.
:::

### Critical

```markdown
:::{danger}
This could cause serious problems!
:::

:::{error}
Something has gone wrong.
:::
```

:::{danger}
This could cause serious problems!
:::

### Positive

```markdown
:::{success}
Everything worked correctly!
:::

:::{example}
Here's a working example.
:::
```

:::{success}
Everything worked correctly!
:::

### Navigation

```markdown
:::{seealso}
- [[docs/getting-started|Getting Started]]
- [[docs/reference|API Reference]]
:::
```

:::{seealso}
- Related documentation links
- Cross-references to other pages
:::

## Callout Quick Reference

| Type | Use For | Color |
|------|---------|-------|
| `note` | Background info | Blue |
| `info` | Additional context | Blue |
| `tip` | Best practices, suggestions | Green |
| `warning` | Caution, potential issues | Orange |
| `caution` | Proceed carefully | Orange |
| `danger` | Critical warnings | Red |
| `error` | Problems, failures | Red |
| `success` | Positive outcomes | Green |
| `example` | Working examples | Violet |
| `seealso` | Related links, navigation | Blue |

## Custom Titles

Override the default title:

```markdown
:::{warning} Database Migration Required
You must run migrations before deploying this version.
:::
```

:::{warning} Database Migration Required
You must run migrations before deploying this version.
:::

## Rich Content in Callouts

Callouts support full Markdown:

```markdown
:::{tip} Pro Tip: Use Environment Variables
Store sensitive values in environment variables:

1. Create a `.env` file
2. Add your secrets:
   ```bash
   API_KEY=your_secret_key
   ```
3. Reference in config: `${API_KEY}`

See [[docs/building/configuration|Configuration Guide]] for more.
:::
```

:::{tip} Pro Tip: Use Environment Variables
Store sensitive values in environment variables:

1. Create a `.env` file
2. Add your secrets
3. Reference in config

See the Configuration Guide for more.
:::

## Collapsible Callouts

Make callouts collapsible with the `dropdown` directive:

```markdown
:::{dropdown} Click to see the answer
:icon: question

The answer is 42.
:::
```

:::{dropdown} Click to see the answer
:icon: question

The answer is 42.
:::

### Dropdown Options

| Option | Description | Example |
|--------|-------------|---------|
| `:open:` | Start expanded | `:open:` |
| `:icon:` | Custom icon | `:icon: info` |
| `:badge:` | Badge text | `:badge: Advanced` |
| `:color:` | Color variant | `:color: warning` |
| `:description:` | Secondary text | `:description: More details` |
| `:class:` | CSS class | `:class: custom` |

Available colors: `success`, `warning`, `danger`, `info`, `minimal`

## Checklists

For action items or requirements, use checklists:

```markdown
:::{checklist} Before You Deploy
- Run all tests
- Update changelog
- Tag the release
- Notify the team
:::
```

:::{checklist} Before You Deploy
- Run all tests
- Update changelog
- Tag the release
- Notify the team
:::

### Checklist Options

| Option | Description | Example |
|--------|-------------|---------|
| `:style:` | Visual style | `:style: numbered` |
| `:show-progress:` | Display completion bar | `:show-progress:` |
| `:compact:` | Tighter spacing | `:compact:` |

Available styles: `default`, `numbered`, `minimal`

```markdown
:::{checklist} Setup Progress
:style: numbered
:show-progress:
- [x] Install dependencies
- [x] Configure environment
- [ ] Run migrations
:::
```

## When to Use Callouts

:::{tip}
**Use callouts sparingly.** Too many callouts reduce their impact. Reserve them for genuinely important information.
:::

### Good Uses

- **note**: Prerequisites, background context
- **tip**: Best practices, helpful shortcuts
- **warning**: Common mistakes, gotchas
- **danger**: Security issues, data loss risks
- **seealso**: Related pages, cross-references

### Avoid

- Using callouts for routine information
- Stacking multiple callouts back-to-back
- Putting critical instructions inside callouts (main content should stand alone)

## Best Practices

:::{checklist}
- Use the appropriate type for the content severity
- Keep callouts brief and scannable
- Don't bury critical instructions in callouts
- Use custom titles for specific warnings
- Limit to 1-2 callouts per section
:::

::::{seealso}
- [[docs/reference/directives/admonitions|Admonitions Reference]] — Complete options
- [[docs/content/authoring/interactive|Interactive Elements]] — Dropdowns and more
::::
