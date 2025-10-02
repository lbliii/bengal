---
title: "Creating Custom Templates"
date: 2025-09-12
tags: ["templates", "customization", "advanced"]
description: "Build custom templates for your Bengal site"
---

# Creating Custom Templates

Bengal uses Jinja2 for templating, giving you powerful template features.

## Template Inheritance

```jinja2
{% extends "base.html" %}

{% block content %}
  <h1>{{ page.title }}</h1>
  {{ content }}
{% endblock %}
```

## Template Variables

All pages have access to:
- `page`: Current page object
- `site`: Site configuration
- `content`: Rendered content

## Filters

Use Jinja2 filters:

```jinja2
{{ page.date | date_format("%B %d, %Y") }}
```

