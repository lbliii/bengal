---
title: Create Custom Skeletons
nav_title: Custom Skeletons
description: Build reusable site structure templates with skeleton YAML
draft: false
weight: 60
lang: en
tags:
- skeleton
- yaml
- scaffolding
- templates
keywords:
- skeleton
- yaml
- custom templates
- site structure
- scaffolding
category: extending
icon: file-text
---

# Create Custom Skeletons

Skeleton YAML files define reusable site structures. Create one skeleton, apply it to any project.

## When to Use Custom Skeletons

- **Team standards**: Enforce consistent site architecture across projects
- **Repeatable patterns**: Scaffold the same structure without copy-paste
- **Onboarding**: New team members get a working structure immediately
- **Experiments**: Quickly test different information architectures

## Skeleton Anatomy

A skeleton has two sections: **metadata** and **structure**.

```yaml
# Metadata
name: My Custom Skeleton
description: What this skeleton creates
version: "1.0"

# Global cascade (optional)
cascade:
  type: doc

# Page structure
structure:
  - path: _index.md
    props:
      title: Home
    content: |
      # Welcome
```

## Build a Skeleton Step by Step

### Step 1: Define Metadata

```yaml
name: API Documentation
description: OpenAPI-style docs with endpoints and schemas
version: "1.0"
```

### Step 2: Add Global Cascade

Cascade settings apply to all pages unless overridden:

```yaml
cascade:
  type: doc
  draft: false
```

### Step 3: Define Root Pages

```yaml
structure:
  - path: _index.md
    props:
      title: API Reference
      description: Complete API documentation
      weight: 100
    content: |
      # API Reference

      Welcome to the API documentation.

      ## Sections

      - [Authentication](/authentication)
      - [Endpoints](/endpoints)
      - [Schemas](/schemas)
```

### Step 4: Add Sections with Nested Pages

Use `pages` to nest content under a section:

```yaml
  - path: endpoints/_index.md
    props:
      title: Endpoints
      weight: 20
    cascade:
      type: doc
    content: |
      # API Endpoints

      All available endpoints.

    pages:
      - path: users.md
        props:
          title: Users
          weight: 10
        content: |
          # Users Endpoint

          `GET /api/users`

          Returns a list of users.

      - path: posts.md
        props:
          title: Posts
          weight: 20
        content: |
          # Posts Endpoint

          `GET /api/posts`

          Returns a list of posts.
```

### Step 5: Apply and Test

```bash
# Preview first
bengal project skeleton apply api-docs.yaml --dry-run

# Apply
bengal project skeleton apply api-docs.yaml

# Serve
bengal serve
```

## Complete Example: API Documentation Skeleton

```yaml
name: API Documentation
description: REST API docs with authentication, endpoints, and schemas
version: "1.0"

cascade:
  type: doc

structure:
  - path: _index.md
    props:
      title: API Reference
      description: Complete API documentation
      weight: 100
    content: |
      # API Reference

      This documentation covers all available API endpoints.

      ## Quick Links

      - [Authentication](/authentication) - API keys and OAuth
      - [Endpoints](/endpoints) - Available endpoints
      - [Schemas](/schemas) - Request/response formats
      - [Errors](/errors) - Error codes and handling

  - path: authentication.md
    props:
      title: Authentication
      weight: 10
    content: |
      # Authentication

      All API requests require authentication.

      ## API Keys

      Include your API key in the header:

      ```bash
      curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://api.example.com/v1/users
      ```

      ## OAuth 2.0

      For user-authenticated requests, use OAuth 2.0.

  - path: endpoints/_index.md
    props:
      title: Endpoints
      weight: 20
    content: |
      # API Endpoints

      All available REST endpoints.

    pages:
      - path: users.md
        props:
          title: Users
          weight: 10
        content: |
          # Users

          ## List Users

          ```http
          GET /api/v1/users
          ```

          ## Get User

          ```http
          GET /api/v1/users/{id}
          ```

          ## Create User

          ```http
          POST /api/v1/users
          ```

      - path: posts.md
        props:
          title: Posts
          weight: 20
        content: |
          # Posts

          ## List Posts

          ```http
          GET /api/v1/posts
          ```

          ## Get Post

          ```http
          GET /api/v1/posts/{id}
          ```

  - path: schemas/_index.md
    props:
      title: Schemas
      weight: 30
    content: |
      # Data Schemas

      Request and response formats.

    pages:
      - path: user.md
        props:
          title: User Schema
        content: |
          # User Schema

          ```json
          {
            "id": "string",
            "email": "string",
            "name": "string",
            "created_at": "datetime"
          }
          ```

      - path: post.md
        props:
          title: Post Schema
        content: |
          # Post Schema

          ```json
          {
            "id": "string",
            "title": "string",
            "body": "string",
            "author_id": "string",
            "published_at": "datetime"
          }
          ```

  - path: errors.md
    props:
      title: Error Handling
      weight: 40
    content: |
      # Error Handling

      ## Error Response Format

      ```json
      {
        "error": {
          "code": "string",
          "message": "string"
        }
      }
      ```

      ## Common Error Codes

      | Code | Description |
      |------|-------------|
      | 400 | Bad Request |
      | 401 | Unauthorized |
      | 404 | Not Found |
      | 429 | Rate Limited |
      | 500 | Server Error |
```

## Props Reference

Common frontmatter fields for `props`:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title (required) |
| `description` | string | SEO description |
| `weight` | number | Sort order (lower = first) |
| `date` | string | Publication date (ISO format) |
| `tags` | list | Taxonomy tags |
| `draft` | boolean | Exclude from production |
| `type` | string | Content type (`doc`, `blog`, etc.) |
| `layout` | string | Layout variant |
| `nav_title` | string | Short title for navigation |

Custom props are accessible in templates via `page.props.fieldname`.

## Dynamic Placeholders

Use `{{date}}` for the current date:

```yaml
- path: posts/new-post.md
  props:
    title: New Post
    date: "{{date}}"
  content: |
    # New Post
    Written on {{date}}.
```

## Cascade Patterns

### Section-Level Cascade

Apply settings to all pages in a section:

```yaml
- path: blog/_index.md
  props:
    title: Blog
  cascade:
    type: blog
    author: Default Author
  pages:
    - path: post-1.md
      props:
        title: First Post  # Inherits type: blog, author: Default Author
```

### Override Cascade

Child pages can override cascaded values:

```yaml
- path: docs/_index.md
  cascade:
    type: doc
    draft: false
  pages:
    - path: wip.md
      props:
        title: Work in Progress
        draft: true  # Overrides cascade
```

## Tips

:::{tip} Version Your Skeletons
Include `version` in metadata. When you update the skeleton, increment the version:

```yaml
name: Team Docs
version: "2.0"  # Breaking changes from 1.x
```
:::

:::{tip} Organize by Purpose
Create separate skeletons for different use cases:

```
skeletons/
├── api-docs.yaml
├── blog.yaml
├── landing-page.yaml
└── product-docs.yaml
```
:::

:::{tip} Test with Dry Run
Always preview before applying:

```bash
bengal project skeleton apply my-skeleton.yaml --dry-run
```
:::

## Troubleshooting

### Files Not Created

**Symptom**: `bengal project skeleton apply` reports 0 files created.

**Cause**: Files already exist and `--force` was not used.

**Fix**:

```bash
bengal project skeleton apply my-skeleton.yaml --force
```

### Content Not Rendering

**Symptom**: YAML content appears as raw text.

**Cause**: Incorrect indentation in `content` block.

**Fix**: Use `|` for multiline content and indent consistently:

```yaml
content: |
  # Title

  Paragraph text.

  - List item
```

### Cascade Not Applied

**Symptom**: Child pages don't inherit cascade settings.

**Cause**: `cascade` is at the wrong level.

**Fix**: Place `cascade` inside the parent page definition, not inside `props`:

```yaml
# Correct
- path: docs/_index.md
  cascade:
    type: doc

# Wrong
- path: docs/_index.md
  props:
    cascade:  # This won't work
      type: doc
```

## Next Steps

- [[docs/tutorials/sites/skeleton-quickstart|Skeleton YAML Quickstart]] — Copy-paste examples
- [[docs/get-started/scaffold-your-site|Scaffold Tutorial]] — Full walkthrough
- [[docs/reference/site-templates|Site Templates Reference]] — Built-in templates
