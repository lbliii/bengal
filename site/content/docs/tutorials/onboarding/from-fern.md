---
title: From Fern
nav_title: Fern
description: Onboarding guide for Fern Docs users migrating to Bengal
weight: 40
tags:
- tutorial
- migration
- fern
- api-docs
- sdk
keywords:
- fern
- fern docs
- api documentation
- sdk generation
- migration
- docs.yml
---

# Bengal for Fern Users

Fern is powerful for API-first teams with SDK generation. Bengal focuses purely on documentation—giving you full control over your content without proprietary syntax. If you're migrating away from Fern's docs platform, this guide shows you how.

## Quick Wins (5 Minutes)

### Understanding the Difference

| Aspect | Fern | Bengal |
|--------|------|--------|
| Primary focus | API + SDK + Docs | Documentation only |
| Configuration | `fern.config.json` + `docs.yml` | `bengal.toml` |
| Content format | MDX (proprietary extensions) | Standard Markdown |
| Hosting | Fern-hosted | Self-hosted anywhere |
| SDK generation | Built-in | External tools |

### What Transfers Directly

| Fern | Bengal | Status |
|------|--------|--------|
| MDX content | Markdown | ✅ Convert syntax |
| OpenAPI specs | OpenAPI support | ✅ Works directly |
| Navigation structure | Directory-based nav | ✅ Simpler |
| Code examples | Code blocks | ✅ Identical |

---

## Component → Directive Translation

### Callouts

:::{tab-set}

:::{tab} Fern (MDX)
```jsx
<Callout intent="info">
  This is an informational callout.
</Callout>

<Callout intent="warning">
  This is a warning callout.
</Callout>

<Callout intent="success">
  Operation completed successfully.
</Callout>

<Callout intent="danger">
  Critical warning—proceed with caution.
</Callout>
```
:::{/tab}

:::{tab} Bengal (Clean Markdown!)
```markdown
:::{info}
This is an informational callout.
:::

:::{warning}
This is a warning callout.
:::

:::{tip}
Operation completed successfully.
:::

:::{danger}
Critical warning—proceed with caution.
:::
```
:::{/tab}

:::{/tab-set}

### Tabs / Code Examples

:::{tab-set}

:::{tab} Fern (MDX)
```jsx
<CodeBlocks>
  <CodeBlock title="Python">
    ```python
    import fern
    client = fern.Client(api_key="...")
    ```
  </CodeBlock>
  <CodeBlock title="TypeScript">
    ```typescript
    import { FernClient } from "fern";
    const client = new FernClient({ apiKey: "..." });
    ```
  </CodeBlock>
  <CodeBlock title="Go">
    ```go
    client := fern.NewClient(fern.WithAPIKey("..."))
    ```
  </CodeBlock>
</CodeBlocks>
```
:::{/tab}

:::{tab} Bengal
````markdown
:::{tab-set}
:::{tab} Python
```python
import myapi
client = myapi.Client(api_key="...")
```
:::{/tab}
:::{tab} TypeScript
```typescript
import { MyAPIClient } from "myapi";
const client = new MyAPIClient({ apiKey: "..." });
```
:::{/tab}
:::{tab} Go
```go
client := myapi.NewClient(myapi.WithAPIKey("..."))
```
:::{/tab}
:::{/tab-set}
````
:::{/tab}

:::{/tab-set}

### Cards

:::{tab-set}

:::{tab} Fern (MDX)
```jsx
<Cards>
  <Card
    title="Getting Started"
    icon="rocket"
    href="/docs/getting-started"
  >
    Set up your first integration in minutes.
  </Card>
  <Card
    title="API Reference"
    icon="book"
    href="/docs/api-reference"
  >
    Complete reference for all endpoints.
  </Card>
</Cards>
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{cards}
:columns: 2

:::{card} Getting Started
:icon: rocket
:link: /docs/getting-started/

Set up your first integration in minutes.
:::{/card}

:::{card} API Reference
:icon: book
:link: /docs/api-reference/

Complete reference for all endpoints.
:::{/card}

:::{/cards}
```
:::{/tab}

:::{/tab-set}

### Accordions

:::{tab-set}

:::{tab} Fern (MDX)
```jsx
<Accordion title="How do I authenticate?">
  Use the `Authorization` header with your API key:
  ```
  Authorization: Bearer YOUR_API_KEY
  ```
</Accordion>

<Accordion title="What are the rate limits?">
  We allow 1000 requests per minute per API key.
</Accordion>
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{dropdown} How do I authenticate?
:icon: key

Use the `Authorization` header with your API key:
```
Authorization: Bearer YOUR_API_KEY
```
:::

:::{dropdown} What are the rate limits?
:icon: clock

We allow 1000 requests per minute per API key.
:::
```
:::{/tab}

:::{/tab-set}

### Steps / Guides

:::{tab-set}

:::{tab} Fern (MDX)
```jsx
<Steps>
  <Step title="Install the SDK">
    ```bash
    npm install @your-company/sdk
    ```
  </Step>
  <Step title="Initialize">
    ```typescript
    import { Client } from "@your-company/sdk";
    const client = new Client({ apiKey: "..." });
    ```
  </Step>
  <Step title="Make a request">
    ```typescript
    const users = await client.users.list();
    ```
  </Step>
</Steps>
```
:::{/tab}

:::{tab} Bengal
````markdown
:::{steps}

:::{step} Install the SDK
```bash
npm install @your-company/sdk
```
:::{/step}

:::{step} Initialize
```typescript
import { Client } from "@your-company/sdk";
const client = new Client({ apiKey: "..." });
```
:::{/step}

:::{step} Make a request
```typescript
const users = await client.users.list();
```
:::{/step}

:::{/steps}
````
:::{/tab}

:::{/tab-set}

### API Endpoint Documentation

:::{tab-set}

:::{tab} Fern (from OpenAPI + custom)
```yaml
# Fern generates from your API definition
# Custom docs in MDX reference generated content

<EndpointRequestSnippet endpoint="GET /users" />
<EndpointResponseSnippet endpoint="GET /users" />
```
:::{/tab}

:::{tab} Bengal (Table + OpenAPI)
```markdown
## List Users

`GET /users`

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum results (default: 20) |
| `offset` | integer | No | Pagination offset |

### Response

| Field | Type | Description |
|-------|------|-------------|
| `users` | array | List of user objects |
| `total` | integer | Total count |

### Example

```bash
curl -X GET "https://api.example.com/users?limit=10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

<!-- Or use OpenAPI directive -->
:::{openapi} openapi.yaml
:path: /users
:method: GET
:::
```
:::{/tab}

:::{/tab-set}

---

## Configuration Comparison

### Basic Config

:::{tab-set}

:::{tab} Fern (fern.config.json + docs.yml)
```json
// fern.config.json
{
  "organization": "your-org",
  "version": "0.x.x"
}
```

```yaml
# docs.yml
instances:
  - url: https://docs.your-company.com

title: Your Company Docs

navigation:
  - section: Getting Started
    contents:
      - page: Introduction
        path: ./pages/introduction.mdx
      - page: Quickstart
        path: ./pages/quickstart.mdx
  - section: API Reference
    contents:
      - api: API Reference

colors:
  accentPrimary: "#0D9373"

logo:
  light: ./assets/logo-light.svg
  dark: ./assets/logo-dark.svg
```
:::{/tab}

:::{tab} Bengal (bengal.toml)
```toml
[site]
title = "Your Company Docs"
baseurl = "https://docs.your-company.com"
theme = "bengal"

[site.logo]
light = "assets/logo-light.svg"
dark = "assets/logo-dark.svg"

# Navigation auto-generated from directory structure
# Use weight frontmatter for ordering

# OpenAPI integration
[autodoc.openapi]
enabled = true
spec = "openapi.yaml"
```
:::{/tab}

:::{/tab-set}

### Navigation

:::{tab-set}

:::{tab} Fern (docs.yml)
```yaml
navigation:
  - section: Getting Started
    contents:
      - page: Introduction
        path: ./pages/introduction.mdx
      - page: Quickstart
        path: ./pages/quickstart.mdx
      - page: Authentication
        path: ./pages/authentication.mdx
  - section: Guides
    contents:
      - page: Webhooks
        path: ./pages/guides/webhooks.mdx
      - page: Pagination
        path: ./pages/guides/pagination.mdx
  - section: API Reference
    contents:
      - api: API Reference
```
:::{/tab}

:::{tab} Bengal (Directory structure)
```bash
# Navigation from directory structure + weight frontmatter:

content/
├── docs/
│   ├── getting-started/
│   │   ├── _index.md (weight: 10)
│   │   ├── introduction.md (weight: 10)
│   │   ├── quickstart.md (weight: 20)
│   │   └── authentication.md (weight: 30)
│   ├── guides/
│   │   ├── _index.md (weight: 20)
│   │   ├── webhooks.md (weight: 10)
│   │   └── pagination.md (weight: 20)
│   └── api-reference/
│       ├── _index.md (weight: 30)
│       └── ... (generated from OpenAPI)
```
:::{/tab}

:::{/tab-set}

:::{tip}
No manual `docs.yml` updates when you add pages. Bengal's directory structure *is* the navigation.
:::

---

## What You Don't Need Anymore

| Fern Requires | Bengal |
|---------------|--------|
| `fern.config.json` | Not needed |
| `docs.yml` navigation | Auto-generated |
| Fern CLI (`fern generate`) | `bengal build` |
| Fern hosting | Any static host |
| Proprietary MDX syntax | Standard markdown |
| Fern organization account | Self-hosted |

---

## Feature Comparison

### What Bengal Has

| Feature | Fern | Bengal |
|---------|------|--------|
| Callouts | `<Callout>` | `:::{note}`, `:::{warning}` ✅ |
| Tabs | `<CodeBlocks>` | `:::{tab-set}` ✅ |
| Cards | `<Cards>` | `:::{cards}` ✅ |
| Steps | `<Steps>` | `:::{steps}` ✅ |
| Accordions | `<Accordion>` | `:::{dropdown}` ✅ |
| Code blocks | Built-in | Built-in ✅ |
| OpenAPI | Built-in | `:::{openapi}` or autodoc ✅ |
| Search | Built-in | Built-in ✅ |
| Dark mode | Built-in | Built-in ✅ |
| Custom domains | Paid feature | Any host |

### What's Different (Trade-offs)

| Feature | Fern | Bengal | Notes |
|---------|------|--------|-------|
| SDK generation | Built-in | External | Use OpenAPI Generator, etc. |
| API playground | Interactive | Static | External tools for testing |
| Type-safe API definitions | Fern Definition | OpenAPI | Standard spec works |
| Hosting | Managed | Self-hosted | More control |
| AI-powered search | Built-in | External | Integrate your own |

### What Bengal Adds

| Feature | Description |
|---------|-------------|
| Full source control | Modify anything |
| No vendor lock-in | Standard formats |
| Offline development | Complete local workflow |
| Build-time validation | `bengal health` checks |
| Content versioning | `_versions/` folders |
| Custom themes | Full theming control |

---

## SDK Generation Alternative

Fern's SDK generation is separate from documentation. Without Fern, you can use:

```bash
# OpenAPI Generator (most languages)
openapi-generator generate -i openapi.yaml -g python -o ./sdk/python

# For TypeScript specifically
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-fetch \
  -o ./sdk/typescript

# Or use language-specific tools:
# Python: openapi-python-client
# Go: oapi-codegen
# Rust: openapi-generator with rust templates
```

Your OpenAPI spec works with any generator. Documentation is independent of SDK generation.

---

## Directory Structure Comparison

| Fern | Bengal | Notes |
|------|--------|-------|
| `fern/` | Project root | Simpler structure |
| `fern/docs/pages/` | `content/docs/` | Content location |
| `fern/docs/assets/` | `assets/` | Static files |
| `fern.config.json` | Not needed | No central config |
| `docs.yml` | `bengal.toml` + directories | Simpler |
| `fern/openapi/` | Project root or `api/` | Flexible location |

---

## What Bengal Adds

:::::{tab-set}

::::{tab} Content Variables
```markdown
---
title: API Reference
api_version: "2.0"
base_url: "https://api.example.com/v2"
---

# {{ page.title }}

Current version: **{{ page.metadata.api_version }}**
Base URL: `{{ page.metadata.base_url }}`
```

Use template variables directly in markdown.
::::{/tab}

::::{tab} Reusable Snippets
```markdown
<!-- _snippets/auth-note.md -->
:::{note}
All API requests require authentication.
Include your API key in the `Authorization` header.
:::

<!-- In any page -->
:::{include} /_snippets/auth-note.md
:::
```

DRY principle for documentation.
::::{/tab}

::::{tab} Build Validation
```bash
# Check all links
bengal health linkcheck

# Full health check
bengal health

# Analyze site structure
bengal analyze
```

Catch problems before they reach users.
::::{/tab}

::::{tab} No Lock-in
```bash
# Deploy anywhere
bengal build
# Output is static HTML

# Works with:
# - GitHub Pages
# - Netlify
# - Vercel
# - Cloudflare Pages
# - AWS S3 + CloudFront
# - Any web server
```
::::{/tab}

:::::{/tab-set}

---

## Migration Steps

:::{steps}

:::{step} Install Bengal
```bash
pip install bengal
# or with uv
uv add bengal
```
:::{/step}

:::{step} Create New Site
```bash
bengal new site mysite
cd mysite
```
:::{/step}

:::{step} Copy Content
```bash
# Copy your Fern MDX files
cp -r /path/to/fern/docs/pages/* content/docs/

# Copy assets
cp -r /path/to/fern/docs/assets/* assets/

# Copy OpenAPI spec
cp /path/to/fern/openapi/openapi.yaml .
```
:::{/step}

:::{step} Convert MDX Syntax
Replace Fern components with directives:

| Find | Replace With |
|------|--------------|
| `<Callout intent="info">` | `:::{info}` |
| `<Callout intent="warning">` | `:::{warning}` |
| `<Callout intent="success">` | `:::{tip}` |
| `<Callout intent="danger">` | `:::{danger}` |
| `<CodeBlocks>` | `:::{tab-set}` |
| `<CodeBlock title="X">` | `:::{tab} X` |
| `<Cards>` | `:::{cards}` |
| `<Card>` | `:::{card}` |
| `<Steps>` | `:::{steps}` |
| `<Step>` | `:::{step}` |
| `<Accordion>` | `:::{dropdown}` |
:::{/step}

:::{step} Rename Files
```bash
# Rename .mdx to .md
find content -name "*.mdx" -exec sh -c 'mv "$1" "${1%.mdx}.md"' _ {} \;

# Create section index files
# For each directory, create _index.md
```
:::{/step}

:::{step} Add Frontmatter
Add ordering to pages:

```yaml
---
title: Quickstart
weight: 20
description: Get started in 5 minutes
---
```
:::{/step}

:::{step} Configure OpenAPI (Optional)
If using OpenAPI for API reference:

```yaml
# config/_default/autodoc.yaml
autodoc:
  openapi:
    enabled: true
    specs:
      - path: "openapi.yaml"
        output_prefix: "api-reference"
```
:::{/step}

:::{step} Test
```bash
bengal build
bengal health linkcheck
bengal serve
```
:::{/step}

:::{/steps}

---

## Migration Checklist

:::{checklist} Before You Start
- [ ] Install Bengal: `pip install bengal`
- [ ] Export/download your Fern content
- [ ] Create new Bengal site: `bengal new site mysite`
:::

:::{checklist} Content Migration
- [ ] Copy MDX files to `content/docs/`
- [ ] Rename `.mdx` to `.md`
- [ ] Convert `<Callout>` to `:::{note}`, etc.
- [ ] Convert `<CodeBlocks>` to `:::{tab-set}`
- [ ] Convert `<Cards>` to `:::{cards}`
- [ ] Convert `<Steps>` to `:::{steps}`
- [ ] Remove Fern-specific imports
:::

:::{checklist} Configuration
- [ ] Create `bengal.toml`
- [ ] Add `weight` frontmatter for ordering
- [ ] Create `_index.md` for each section
- [ ] Configure OpenAPI autodoc if used
:::

:::{checklist} Assets
- [ ] Copy images to `assets/`
- [ ] Update image paths in content
- [ ] Copy OpenAPI specs
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | Fern | Bengal |
|------|------|--------|
| Install | `npm install fern-api` | `pip install bengal` |
| Initialize | `fern init` | `bengal new site` |
| Generate | `fern generate` | `bengal build` |
| Serve | Fern hosting | `bengal serve` |
| Deploy | Push to Fern | Any static host |
| Callout | `<Callout>` | `:::{note}` |
| Tabs | `<CodeBlocks>` | `:::{tab-set}` |
| Cards | `<Cards>` | `:::{cards}` |
| Steps | `<Steps>` | `:::{steps}` |

---

## Common Questions

:::{dropdown} Why leave Fern?
:icon: question

Common reasons for migration:
- **Vendor lock-in**: Fern's proprietary syntax and hosting
- **Cost**: Self-hosted Bengal is free
- **Control**: Full customization of output
- **Simplicity**: Documentation without SDK complexity
- **Flexibility**: Deploy anywhere, modify anything
:::

:::{dropdown} What about SDK generation?
:icon: question

SDK generation and documentation are separate concerns. For SDKs without Fern:

```bash
# OpenAPI Generator supports 50+ languages
openapi-generator generate -i openapi.yaml -g python

# Or use specialized tools:
# - openapi-python-client (Python)
# - openapi-typescript (TypeScript)
# - oapi-codegen (Go)
```

Your OpenAPI spec is the source of truth—it works everywhere.
:::

:::{dropdown} Can I keep my OpenAPI workflow?
:icon: question

Absolutely. Bengal works great with OpenAPI:

```yaml
# config/_default/autodoc.yaml
autodoc:
  openapi:
    enabled: true
    specs:
      - path: "openapi.yaml"
        generate_pages: true
```

Or inline in pages:

```markdown
:::{openapi} openapi.yaml
:path: /users/{id}
:method: GET
:::
```
:::

:::{dropdown} What about the API playground?
:icon: question

For interactive API testing, use external tools:
- [Swagger UI](https://swagger.io/tools/swagger-ui/) (can embed)
- [Stoplight Elements](https://stoplight.io/open-source/elements)
- [RapiDoc](https://rapidocweb.com/)
- [Postman](https://www.postman.com/) (link to collections)

Static documentation with links to testing tools is often clearer than embedded playgrounds.
:::

:::{dropdown} How do I handle versioning?
:icon: question

Bengal supports documentation versioning:

```text
content/
├── docs/              # Current version
├── _versions/
│   ├── v1/
│   │   └── docs/      # v1 documentation
│   └── v2/
│       └── docs/      # v2 documentation
```

Version switcher appears automatically in navigation.
:::

---

## Next Steps

- [Directives Reference](/docs/reference/directives/) - All available directives
- [Writer Quickstart](/docs/get-started/quickstart-writer/) - Full markdown guide
- [Configuration Reference](/docs/building/configuration/) - Config options
- [OpenAPI Autodoc](/docs/content/sources/autodoc/) - API doc generation
