---
title: "Users API"
description: "Manage users with the DataFlow API"
---

# Users API

The {{ page.metadata.product_name }} {{ page.metadata.product_version }} Users API allows you to create, read, update, and delete user records.

## Base URL

All user endpoints are available at:
```
{{ page.metadata.api_base_url }}/users
```

## List Users

Get a paginated list of users.

**Endpoint:** `GET {{ page.metadata.api_base_url }}/users`

**Example Request:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     {{ page.metadata.api_base_url }}/users?page=1&limit=10
```

**Response:**
```json
{
  "users": [...],
  "total": 42,
  "page": 1,
  "api_version": "{{ page.metadata.product_version }}"
}
```

## Get User by ID

Retrieve a specific user by their ID.

**Endpoint:** `GET {{ page.metadata.api_base_url }}/users/{id}`

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     {{ page.metadata.api_base_url }}/users/12345
```

## Create User

Create a new user in {{ page.metadata.product_name }}.

**Endpoint:** `POST {{ page.metadata.api_base_url }}/users`

**New in {{ page.metadata.product_version }}:** Support for custom user attributes.

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name": "John Doe", "email": "john@example.com"}' \
     {{ page.metadata.api_base_url }}/users
```

## Update User

Update an existing user.

**Endpoint:** `PATCH {{ page.metadata.api_base_url }}/users/{id}`

## Delete User

Delete a user by ID.

**Endpoint:** `DELETE {{ page.metadata.api_base_url }}/users/{id}`

---

## SDK Examples

### Python

```python
from dataflow import Client

# Initialize client for {{ page.metadata.product_version }}
client = Client(
    base_url="{{ page.metadata.api_base_url }}",
    api_key="YOUR_API_KEY"
)

# List users
users = client.users.list(page=1, limit=10)
```

### JavaScript

```javascript
// DataFlow {{ page.metadata.product_version }} SDK
const dataflow = require('@dataflow/sdk');

const client = new dataflow.Client({
  baseUrl: '{{ page.metadata.api_base_url }}',
  apiKey: 'YOUR_API_KEY'
});

// Get user
const user = await client.users.get('12345');
```

---

*{{ page.metadata.product_name }} {{ page.metadata.product_version }} - Released {{ page.metadata.release_date }}*

