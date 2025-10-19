---
title: Template Guide
author: Test Author
---

# Template Functions Guide

## Variable Substitution

Use {{/* page.title */}} to display the page title.

## String Functions

Truncate content:

```jinja2
{{/* post.content | truncatewords(50) */}}
```

## Date Functions

Format dates:

```jinja2
{{/* page.date | format_date('%Y-%m-%d') */}}
```

## URL Functions

Absolute URLs:

```jinja2
{{/* page.url | absolute_url */}}
```
