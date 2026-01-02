---
title: Block Syntax
nav_title: Blocks
description: Control flow blocks, endings, and pattern matching
weight: 10
type: doc
tags:
- reference
- kida
- syntax
---

Kida uses `{% end %}` for all block endings and adds pattern matching for cleaner conditionals.

## Unified Block Endings

Kida uses `{% end %}` for all block endings, eliminating the need to remember specific closing tags:

```kida
{% if page.draft %}
  <span class="draft">Draft</span>
{% end %}

{% for post in posts %}
  <article>{{ post.title }}</article>
{% end %}

{% block content %}
  {{ page.content | safe }}
{% end %}
```

**Compatibility**: Specific endings like `{% endif %}`, `{% endfor %}`, `{% endwhile %}`, and `{% endblock %}` are also accepted for Jinja2 compatibility. Use `{% end %}` for consistency.

## Conditionals

### If/Elif/Else

Standard conditional blocks:

```kida
{% if page.draft %}
  <span class="badge">Draft</span>
{% elif page.scheduled %}
  <span class="badge">Scheduled</span>
{% else %}
  <span class="badge">Published</span>
{% end %}
```

### Unless

Use `{% unless %}` for negated conditions (Kida-native):

```kida
{% unless page.hidden %}
  <article>{{ page.content | safe }}</article>
{% end %}

{% unless user.logged_in %}
  <a href="/login">Sign in</a>
{% else %}
  <span>Welcome, {{ user.name }}</span>
{% end %}
```

## Loops

### For Loops

```kida
{% for post in posts %}
  <article>
    <h2>{{ post.title }}</h2>
    <p>{{ post.excerpt }}</p>
  </article>
{% end %}
```

### Loop Variables

Access iteration metadata via the `loop` object:

```kida
{% for item in items %}
  {{ loop.index }}      {# 1-indexed: 1, 2, 3... #}
  {{ loop.index0 }}     {# 0-indexed: 0, 1, 2... #}
  {{ loop.first }}       {# true on first iteration #}
  {{ loop.last }}        {# true on last iteration #}
  {{ loop.length }}      {# total items in sequence #}
  {{ loop.revindex }}    {# reverse 1-indexed: length...3, 2, 1 #}
  {{ loop.revindex0 }}   {# reverse 0-indexed: length-1...2, 1, 0 #}
  {{ loop.previtem }}    {# previous item (None on first) #}
  {{ loop.nextitem }}    {# next item (None on last) #}
  {{ loop.cycle('odd', 'even') }}  {# alternates values #}
{% end %}
```

### Empty Clause

Render content when the iterable is empty:

```kida
{% for post in posts %}
  <article>{{ post.title }}</article>
{% empty %}
  <p>No posts found.</p>
{% end %}
```

**Note**: Kida uses `{% empty %}` (not `{% else %}`) for empty iterables, matching Jinja2 behavior.

### Inline Filter

Filter items directly in the loop declaration:

```kida
{% for post in posts if post.published %}
  <article>{{ post.title }}</article>
{% end %}
```

### While Loops

Kida adds `{% while %}` loops (not available in Jinja2):

```kida
{% let counter = 0 %}
{% while counter < 5 %}
  <p>Count: {{ counter }}</p>
  {% let counter = counter + 1 %}
{% end %}
```

**Alternative ending**: You can also use `{% endwhile %}` instead of `{% end %}`.

### Loop Control

```kida
{% for item in items %}
  {% if item.hidden %}
    {% continue %}
  {% end %}
  {% if item.is_final %}
    {{ item.title }}
    {% break %}
  {% end %}
  {{ item.title }}
{% end %}
```

## Pattern Matching

Replace long `if/elif` chains with `{% match %}`:

```kida
{% match page.type %}
  {% case "blog" %}
    <i class="icon-pen"></i> Blog Post
  {% case "doc" %}
    <i class="icon-book"></i> Documentation
  {% case "tutorial" %}
    <i class="icon-graduation-cap"></i> Tutorial
  {% case _ %}
    <i class="icon-file"></i> Page
{% end %}
```

The `{% case _ %}` pattern matches anything (default fallback).

### Nested Pattern Matching

```kida
{% match page.type %}
  {% case "blog" %}
    {% match page.format %}
      {% case "standard" %}
        <article class="blog-standard">{{ page.content | safe }}</article>
      {% case "longform" %}
        <article class="blog-longform">{{ page.content | safe }}</article>
      {% case _ %}
        <article class="blog-default">{{ page.content | safe }}</article>
    {% end %}
  {% case "doc" %}
    <article class="doc">{{ page.content | safe }}</article>
  {% case _ %}
    <article>{{ page.content | safe }}</article>
{% end %}
```

### When to Use Pattern Matching

**Use `{% match %}`** when:

- Checking the same variable against multiple discrete values
- You have 3+ cases
- Cases are strings, numbers, or simple patterns

**Use `{% if %}/{% elif %}`** when:

- Complex boolean expressions (`if x > 10 and y < 5`)
- Range checks or comparisons
- Multiple variable conditions
- Need `unless` semantics

## Range Literals

Kida provides cleaner range syntax:

```kida
{# Inclusive range: 1, 2, 3, 4, 5 #}
{% for i in 1..5 %}
  {{ i }}
{% end %}

{# Exclusive range: 1, 2, 3, 4 #}
{% for i in 1...5 %}
  {{ i }}
{% end %}

{# Range with step: 0, 2, 4, 6, 8, 10 #}
{% for i in 0..10 by 2 %}
  {{ i }}
{% end %}
```

## Complete Example

Combining multiple block types:

```kida
{% extends "baseof.html" %}

{% block content %}
  {% match page.type %}
    {% case "blog" %}
      <article class="blog-post">
        <header>
          <h1>{{ page.title }}</h1>
          {% match page.status %}
            {% case "published" %}
              <span class="status">Published</span>
            {% case "draft" %}
              <span class="status draft">Draft</span>
            {% case _ %}
              <span class="status">Unknown</span>
          {% end %}
        </header>
        <div class="content">
          {{ page.content | safe }}
        </div>
        {% unless page.tags | length == 0 %}
          <footer>
            {% for tag in page.tags if tag.public %}
              <a href="{{ tag_url(tag) }}" class="tag">{{ tag }}</a>
            {% empty %}
              <span>No public tags</span>
            {% end %}
          </footer>
        {% end %}
      </article>
    {% case _ %}
      <article>
        <h1>{{ page.title }}</h1>
        {{ page.content | safe }}
      </article>
  {% end %}
{% end %}
```

**This example demonstrates:**

- Unified `{% end %}` syntax
- Nested pattern matching
- `{% unless %}` for negated conditions
- `{% for %}` with inline filter (`if tag.public`)
- `{% empty %}` clause for empty iterables
