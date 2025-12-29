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
{% endblock %}
```

Jinja2's `{% endblock %}` is also accepted for block endings.

## Conditionals

Standard `if/elif/else`:

```kida
{% if page.draft %}
  <span class="badge">Draft</span>
{% elif page.scheduled %}
  <span class="badge">Scheduled</span>
{% else %}
  <span class="badge">Published</span>
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

```kida
{% for item in items %}
  {{ loop.index }}      {# 1-indexed position #}
  {{ loop.index0 }}     {# 0-indexed position #}
  {{ loop.first }}      {# true for first iteration #}
  {{ loop.last }}       {# true for last iteration #}
  {{ loop.length }}     {# total items #}
{% end %}
```

### While Loops

Kida adds `{% while %}` (not available in Jinja2):

```kida
{% let counter = 0 %}
{% while counter < 5 %}
  <p>Count: {{ counter }}</p>
  {% set counter = counter + 1 %}
{% end %}
```

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

**Use pattern matching** when:

- Checking the same variable against multiple values
- You have 3+ cases
- Cases are discrete values (strings, numbers)

**Use `if/elif`** when:

- Complex boolean expressions
- Range checks (`if x > 10`)
- Multiple variable conditions

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
        {% if page.tags %}
          <footer>
            {% for tag in page.tags %}
              <a href="{{ tag_url(tag) }}" class="tag">{{ tag }}</a>
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
{% endblock %}
```
