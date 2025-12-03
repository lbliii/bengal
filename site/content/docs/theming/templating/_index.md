---
title: Templating
description: Jinja2 templating in Bengal
weight: 10
draft: false
lang: en
tags: [templating, jinja2, layouts]
keywords: [templating, jinja2, layouts, partials, inheritance]
category: guide
---

# Templating

Jinja2 templating fundamentals for Bengal themes.

## Overview

Bengal uses Jinja2 as its template engine, providing:

- **Template inheritance** — Build layouts with extendable blocks
- **Partials** — Reusable template fragments
- **Filters** — Transform data in templates
- **Functions** — Access site data and utilities

## Template Lookup

Bengal searches for templates in order:

1. `layouts/` in your project
2. Theme's `layouts/`
3. Bengal's default templates

## Basic Template

```jinja
{# layouts/single.html #}
{% extends "baseof.html" %}

{% block content %}
<article>
  <h1>{{ page.title }}</h1>
  <div class="content">
    {{ page.content | safe }}
  </div>
</article>
{% endblock %}
```

## Template Inheritance

Base template with blocks:

```jinja
{# layouts/baseof.html #}
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}{{ page.title }}{% endblock %}</title>
  {% block head %}{% endblock %}
</head>
<body>
  {% block header %}{% include "partials/header.html" %}{% endblock %}
  {% block content %}{% endblock %}
  {% block footer %}{% include "partials/footer.html" %}{% endblock %}
</body>
</html>
```

Child template:

```jinja
{% extends "baseof.html" %}

{% block title %}{{ page.title }} | {{ site.title }}{% endblock %}

{% block content %}
  <main>{{ page.content | safe }}</main>
{% endblock %}
```

## In This Section

- **[Layouts](/docs/theming/templating/layouts/)** — Layout patterns and inheritance
- **[Partials](/docs/theming/templating/partials/)** — Reusable template fragments
- **[Functions Reference](/docs/theming/templating/functions/)** — All template functions

