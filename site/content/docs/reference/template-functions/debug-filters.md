---
title: Debug Filters
description: Development helpers for debugging templates
weight: 110
tags:
- reference
- filters
- debug
category: reference
---

# Debug Filters

Development helpers for debugging templates.

## debug

Pretty-print variable for debugging.

```kida
{{ page | debug }}
{{ config | debug(pretty=false) }}
```

## typeof

Get the type of a variable.

```kida
{{ page | typeof }}      {# "Page" #}
{{ "hello" | typeof }}   {# "str" #}
{{ 42 | typeof }}        {# "int" #}
```

## inspect

Inspect object attributes and methods.

```kida
{{ page | inspect }}
{# Properties: title, href, date, ... #}
{# Methods: get_toc(), get_siblings(), ... #}
```
