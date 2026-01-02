---
title: Template Views
description: Use normalized View objects for consistent access to endpoints, schemas, and tags
weight: 60
draft: false
lang: en
tags:
- cookbook
- views
- openapi
- taxonomies
- templates
keywords:
- EndpointView
- SchemaView
- TagView
- template views
- normalized data
- openapi templates
- tag templates
category: cookbook
---

# Template Views

Bengal provides **View objects** that normalize access to complex data in templates. Instead of dealing with different data structures depending on configuration, Views give you consistent properties every time.

## Why Views?

OpenAPI endpoints can come from:
- Individual pages (one file per endpoint)
- Consolidated mode (all endpoints in one section)
- DocElements with typed metadata

Without Views, your template would need conditionals everywhere:

```kida
{# Without Views - messy conditionals #}
{% if endpoint.typed_metadata %}
  {{ endpoint.typed_metadata.method }}
{% elif endpoint.metadata %}
  {{ endpoint.metadata.method }}
{% else %}
  {{ endpoint.method }}
{% end %}
```

With Views, the filter handles all variations:

```kida
{# With Views - clean and consistent #}
{% for ep in section | endpoints %}
  {{ ep.method }} {{ ep.path }}
{% end %}
```

## Available Views

| Filter | Returns | Use For |
|--------|---------|---------|
| `\| endpoints` | `EndpointView[]` | OpenAPI endpoints in a section |
| `\| schemas` | `SchemaView[]` | OpenAPI schemas in a section |
| `\| tag_views` | `TagView[]` | Taxonomy tags with counts |
| `\| tag_view` | `TagView` | Single tag by slug |

---

## EndpointView

Normalize OpenAPI endpoints for templates.

### Usage

```kida
{% let eps = section | endpoints %}

{% for ep in eps %}
<div class="endpoint {{ 'deprecated' if ep.deprecated else '' }}">
  <span class="method method--{{ ep.method | lower }}">{{ ep.method }}</span>
  <a href="{{ ep.href }}">{{ ep.path }}</a>
  <p>{{ ep.summary }}</p>
</div>
{% end %}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `method` | `str` | HTTP method (`GET`, `POST`, `PUT`, `DELETE`, etc.) |
| `path` | `str` | URL path with parameters (`/users/{id}`) |
| `summary` | `str` | Short description |
| `description` | `str` | Full description |
| `deprecated` | `bool` | Whether endpoint is deprecated |
| `href` | `str` | Link to endpoint (anchor or page URL) |
| `has_page` | `bool` | Whether individual page exists |
| `operation_id` | `str \| None` | OpenAPI operationId |
| `tags` | `tuple[str, ...]` | Endpoint tags |
| `typed_metadata` | `Any` | Full `OpenAPIEndpointMetadata` (advanced) |

### Examples

:::{tab-set}
:::{tab-item} API Navigation

```kida
<nav class="api-nav">
  {% for ep in section | endpoints %}
  <a href="{{ ep.href }}" class="api-nav__link">
    <span class="badge badge--{{ ep.method | lower }}">{{ ep.method }}</span>
    {{ ep.path }}
  </a>
  {% end %}
</nav>
```

:::{/tab-item}
:::{tab-item} Endpoint Cards

```kida
<div class="api-cards">
  {% for ep in section | endpoints %}
  <a href="{{ ep.href }}" class="api-card{% if ep.deprecated %} api-card--deprecated{% end %}">
    <header class="api-card__header">
      <span class="method method--{{ ep.method | lower }}">{{ ep.method }}</span>
      <code>{{ ep.path }}</code>
    </header>
    {% if ep.summary %}
    <p class="api-card__summary">{{ ep.summary }}</p>
    {% end %}
    {% if ep.deprecated %}
    <span class="badge badge--warning">Deprecated</span>
    {% end %}
  </a>
  {% end %}
</div>
```

:::{/tab-item}
:::{tab-item} Grouped by Tag

```kida
{# Group endpoints by their first tag #}
{% let eps = section | endpoints %}
{% let by_tag = eps | group_by('tags.0') %}

{% for tag, tag_eps in by_tag %}
<section>
  <h2>{{ tag }}</h2>
  {% for ep in tag_eps %}
    <a href="{{ ep.href }}">{{ ep.method }} {{ ep.path }}</a>
  {% end %}
</section>
{% end %}
```

:::{/tab-item}
:::{/tab-set}

---

## SchemaView

Normalize OpenAPI schemas for templates.

### Usage

```kida
{% let schs = section | schemas %}

{% for schema in schs %}
<div class="schema">
  <a href="{{ schema.href }}">{{ schema.name }}</a>
  <span class="type">{{ schema.schema_type }}</span>
</div>
{% end %}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Schema name (`User`, `OrderRequest`) |
| `schema_type` | `str` | Type (`object`, `array`, `string`, etc.) |
| `description` | `str` | Schema description |
| `href` | `str` | Link to schema page or anchor |
| `has_page` | `bool` | Whether individual page exists |
| `properties` | `dict[str, Any]` | Property definitions |
| `required` | `tuple[str, ...]` | Required property names |
| `enum` | `tuple[Any, ...] \| None` | Enum values (if applicable) |
| `example` | `Any` | Example value (if provided) |
| `typed_metadata` | `Any` | Full `OpenAPISchemaMetadata` (advanced) |

### Examples

:::{tab-set}
:::{tab-item} Schema List

```kida
<div class="schema-list">
  {% for schema in section | schemas %}
  <a href="{{ schema.href }}" class="schema-card">
    <span class="schema-card__name">{{ schema.name }}</span>
    <span class="schema-card__type">{{ schema.schema_type }}</span>
    {% if schema.description %}
    <p class="schema-card__desc">{{ schema.description | truncate(80) }}</p>
    {% end %}
  </a>
  {% end %}
</div>
```

:::{/tab-item}
:::{tab-item} Schema with Properties

```kida
{% for schema in section | schemas %}
<article class="schema-doc">
  <h3>{{ schema.name }}</h3>
  <p>{{ schema.description }}</p>

  {% if schema.properties %}
  <table class="props-table">
    <thead>
      <tr><th>Property</th><th>Required</th></tr>
    </thead>
    <tbody>
      {% for prop_name, prop_def in schema.properties %}
      <tr>
        <td><code>{{ prop_name }}</code></td>
        <td>{{ '✓' if prop_name in schema.required else '' }}</td>
      </tr>
      {% end %}
    </tbody>
  </table>
  {% end %}
</article>
{% end %}
```

:::{/tab-item}
:::{/tab-set}

---

## TagView

Normalize taxonomy tags for templates.

### Usage

```kida
{# All tags #}
{% for tag in site | tag_views %}
  <a href="{{ tag.href }}">{{ tag.name }} ({{ tag.count }})</a>
{% end %}

{# With options #}
{% for tag in site | tag_views(limit=10, sort_by='count') %}
  {{ tag.name }}
{% end %}
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Display name |
| `slug` | `str` | URL-safe slug |
| `href` | `str` | URL to tag page |
| `count` | `int` | Number of posts with this tag |
| `description` | `str` | Tag description (if defined) |
| `percentage` | `float` | Percentage of total posts (for tag clouds) |

### Filter Options

| Option | Default | Description |
|--------|---------|-------------|
| `limit` | `None` | Maximum tags to return |
| `sort_by` | `'count'` | Sort field: `'count'`, `'name'`, or `'percentage'` |

### Examples

:::{tab-set}
:::{tab-item} Tag Cloud

```kida
<div class="tag-cloud">
  {% for tag in site | tag_views %}
  {# Size based on percentage #}
  {% let size = 0.8 + (tag.percentage / 50) %}
  <a href="{{ tag.href }}"
     class="tag-cloud__tag"
     style="font-size: {{ size }}em">
    {{ tag.name }}
  </a>
  {% end %}
</div>
```

:::{/tab-item}
:::{tab-item} Top Tags Sidebar

```kida
<aside class="sidebar-tags">
  <h3>Popular Topics</h3>
  <ul>
    {% for tag in site | tag_views(limit=10, sort_by='count') %}
    <li>
      <a href="{{ tag.href }}">
        {{ tag.name }}
        <span class="count">{{ tag.count }}</span>
      </a>
    </li>
    {% end %}
  </ul>
</aside>
```

:::{/tab-item}
:::{tab-item} Single Tag Lookup

```kida
{# Get a specific tag by slug #}
{% let python_tag = 'python' | tag_view %}

{% if python_tag %}
<div class="featured-tag">
  <a href="{{ python_tag.href }}">
    {{ python_tag.name }} — {{ python_tag.count }} posts
  </a>
  {% if python_tag.description %}
  <p>{{ python_tag.description }}</p>
  {% end %}
</div>
{% end %}
```

:::{/tab-item}
:::{tab-item} Alphabetical List

```kida
<nav class="tag-index">
  {% for tag in site | tag_views(sort_by='name') %}
  <a href="{{ tag.href }}">{{ tag.name }}</a>
  {% end %}
</nav>
```

:::{/tab-item}
:::{/tab-set}

---

## When to Use Views vs Raw Data

| Use Views When | Use Raw Data When |
|----------------|-------------------|
| Building reusable theme components | Custom one-off queries |
| Need consistent property access | Need full page/section access |
| Working with OpenAPI autodoc | Building non-autodoc features |
| Rendering tag clouds/lists | Need raw taxonomy dict |

### Accessing Raw Data

Views are filters on sections or site. You can still access raw data:

```kida
{# Raw page access #}
{% for page in section.pages %}
  {{ page.title }}
{% end %}

{# Raw taxonomy access #}
{% for tag_slug, tag_data in site.taxonomies.tags %}
  {{ tag_data.name }}: {{ tag_data.pages | length }} posts
{% end %}
```

:::{seealso}
- [Template Functions](/docs/theming/templating/functions/) — All available filters
- [OpenAPI Autodoc](/docs/building/automation/autodoc/openapi/) — Generating API docs
- [Taxonomies](/docs/content/organization/taxonomies/) — Tags, categories, and custom taxonomies
:::
