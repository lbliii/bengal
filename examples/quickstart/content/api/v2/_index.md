---
title: "DataFlow API v2.0"
description: "Complete API reference for DataFlow 2.0"
cascade:
  product_name: "DataFlow API"
  product_version: "2.0"
  api_base_url: "https://api.dataflow.example.com/v2"
  release_date: "2025-10-01"
  status: "stable"
  requires_auth: true
---

# DataFlow API v2.0

Welcome to the {{ page.metadata.product_name }} {{ page.metadata.product_version }} documentation.

Released {{ page.metadata.release_date }}, this version includes significant improvements in performance and new features.

## Quick Start

All {{ page.metadata.product_name }} endpoints are available at:
```
{{ page.metadata.api_base_url }}
```

{% if page.metadata.requires_auth %}
**Note:** All API requests require authentication.
{% endif %}

## Available Endpoints

- [Authentication](/api/v2/authentication/)
- [Users API](/api/v2/users/)
- [Data Operations](/api/v2/data-operations/)

