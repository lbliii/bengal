---
title: Template Composition
nav_title: Composition
description: Embed, slot, capture, and import patterns for reusable components
weight: 15
tags:
- reference
- kida
- syntax
---

Kida provides powerful template composition features beyond basic `{% include %}`. These enable component-like patterns for building reusable UI elements.

## Embed (Include with Overrides)

`{% embed %}` includes a template and lets you override its blocks — like `{% include %}` and `{% extends %}` combined:

```kida
{# card-base.html defines blocks: header, body, footer #}
{% embed 'partials/components/card-base.html' with card_variant='compact' %}
  {% block header %}
    <h3>{{ post.title }}</h3>
  {% end %}
  {% block body %}
    <p>{{ post.excerpt }}</p>
  {% end %}
  {% block footer %}
    <time>{{ post.date |> time_ago }}</time>
  {% end %}
{% end %}
```

**When to use `{% embed %}` vs `{% include %}`:**

| Pattern | Use Case |
|---------|----------|
| `{% include %}` | Static partials (footer, nav) — no customization needed |
| `{% embed %}` | Components with slots (cards, modals) — caller customizes regions |
| `{% extends %}` | Page-level inheritance — one parent per template |

Bengal's default theme uses `{% embed %}` with `card-base.html` for all card components (post cards, feature cards, related cards).

## Capture

`{% capture %}` renders content to a variable instead of outputting it. Useful for reusing rendered content in multiple places (e.g., SEO metadata):

```kida
{% capture page_title %}
  {% match page.title %}
  {% case title if title and site.title %}{{ title }} - {{ site.title }}
  {% case title if title %}{{ title }}
  {% case _ %}{{ site.title }}
  {% end %}
{% endcapture %}

{# Use in multiple places #}
<title>{{ page_title | trim }}</title>
<meta property="og:title" content="{{ page_title | trim }}">
```

Bengal's `base.html` uses `{% capture %}` for the page title and meta description.

## Import / From Import

Import reusable functions from other templates:

```kida
{# Import specific functions #}
{% from 'partials/components/cards.html' import related_card, feature_card %}

{# Use them like regular functions #}
{% for post in related_posts %}
  {{ related_card(post) }}
{% end %}
```

This is how Bengal's templates share card components across `page.html`, `post.html`, and `home.html` without duplicating code.

## Def with Slot

Define reusable template functions with `{% def %}`. When combined with `{% call %}`, the caller can pass body content:

```kida
{# Define a wrapper component #}
{% def panel(title, css_class='') %}
<div class="panel {{ css_class }}">
  <h3>{{ title }}</h3>
  <div class="panel-body">
    {{ slot() }}
  </div>
</div>
{% enddef %}

{# Call with body content #}
{% call panel('Warning', css_class='panel-warning') %}
  <p>This action cannot be undone.</p>
{% endcall %}
```

## Complete Component Example

Here's a full component pattern combining `{% embed %}`, `{% def %}`, and `{% from %}`:

```kida
{# partials/components/cards.html #}
{% def related_card(post) %}
{% let post_title = post?.title ?? 'Untitled' %}
{% let post_href = post?.href ?? '#' %}

{% embed 'partials/components/card-base.html' with
    card_variant='compact',
    card_href=post_href,
    gradient_border=true
%}
  {% block header %}
    <h3>{{ post_title }}</h3>
  {% end %}
  {% block footer %}
    {% if post?.date %}
    <time>{{ post.date |> time_ago }}</time>
    {% end %}
  {% end %}
{% end %}
{% enddef %}
```

```kida
{# page.html — import and use #}
{% from 'partials/components/cards.html' import related_card %}

{% for post in page?.related_posts ?? [] %}
  {{ related_card(post) }}
{% end %}
```
