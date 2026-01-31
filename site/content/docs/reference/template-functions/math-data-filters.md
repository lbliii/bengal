---
title: Math & Data Functions
description: Mathematical operations and data file manipulation
weight: 70
tags:
- reference
- filters
- functions
- math
- data
category: reference
---

# Math Filters

Mathematical operations for calculations in templates.

## percentage

Calculate percentage with optional decimal places.

```kida
{{ completed | percentage(total_tasks) }}      {# "75%" #}
{{ score | percentage(max_score, 2) }}         {# "87.50%" #}
```

**Parameters:**
- `part`: Part value
- `total`: Total value
- `decimals`: Number of decimal places (default: 0)

## times

Multiply value by multiplier.

```kida
{{ price | times(1.1) }}      {# Add 10% tax #}
{{ count | times(5) }}        {# Multiply by 5 #}
```

## divided_by

Divide value by divisor. Returns 0 if divisor is 0.

```kida
{{ total | divided_by(count) }}      {# Average #}
{{ seconds | divided_by(60) }}       {# Convert to minutes #}
```

## ceil

Round up to nearest integer.

```kida
{{ 4.2 | ceil }}   {# 5 #}
{{ 4.9 | ceil }}   {# 5 #}
```

## floor

Round down to nearest integer.

```kida
{{ 4.2 | floor }}  {# 4 #}
{{ 4.9 | floor }}  {# 4 #}
```

## round

Round to specified decimal places.

```kida
{{ 4.567 | round }}      {# 5 #}
{{ 4.567 | round(2) }}   {# 4.57 #}
{{ 4.567 | round(1) }}   {# 4.6 #}
```

---

# Data Functions

Functions for loading and manipulating data files.

## get_data

Load data from JSON or YAML file. Returns empty dict if file not found.

```kida
{% let authors = get_data('data/authors.json') %}
{% for author in authors %}
  {{ author.name }}
{% end %}

{% let config = get_data('data/config.yaml') %}
```

## jsonify

Convert data to JSON string.

```kida
{{ data | jsonify }}           {# Compact JSON #}
{{ data | jsonify(2) }}        {# Pretty-printed with indent #}
```

## merge

Merge two dictionaries. Second dict takes precedence.

```kida
{% let config = defaults | merge(custom_config) %}
{% let shallow = dict1 | merge(dict2, deep=false) %}
```

## has_key

Check if dictionary has a key.

```kida
{% if data | has_key('author') %}
  {{ data.author }}
{% end %}
```

## get_nested

Access nested data using dot notation.

```kida
{{ data | get_nested('user.profile.name') }}
{{ data | get_nested('user.email', 'no-email') }}   {# With default #}
```

## keys

Get dictionary keys as list.

```kida
{% for key in data | keys %}
  {{ key }}
{% end %}
```

## values

Get dictionary values as list.

```kida
{% for value in data | values %}
  {{ value }}
{% end %}
```

## items

Get dictionary items as list of (key, value) tuples.

```kida
{% for key, value in data | items %}
  {{ key }}: {{ value }}
{% end %}
```

---

# File Functions

Functions for reading files and checking file existence.

## read_file

Read file contents as string.

```kida
{% let license = read_file('LICENSE') %}
{{ license }}

{% let readme = read_file('docs/README.md') %}
```

## file_exists

Check if file exists.

```kida
{% if file_exists('custom.css') %}
  <link rel="stylesheet" href="{{ asset_url('custom.css') }}">
{% end %}
```

## file_size

Get human-readable file size.

```kida
{{ file_size('downloads/manual.pdf') }}   {# "2.3 MB" #}
{{ file_size('images/hero.png') }}        {# "145.2 KB" #}
```
