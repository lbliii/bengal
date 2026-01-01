---
title: From Mintlify
nav_title: Mintlify
description: Onboarding guide for Mintlify users migrating to Bengal
weight: 35
tags:
- tutorial
- migration
- mintlify
- mdx
- api-docs
keywords:
- mintlify
- mdx
- api documentation
- migration
- mint.json
---

# Bengal for Mintlify Users

Great news: You get the same polished API documentation experience—without the hosted platform lock-in. Bengal's directives provide equivalent components in pure Markdown, and you control your own infrastructure.

## Quick Wins (5 Minutes)

### Core Similarity

Both tools focus on beautiful API documentation with rich components. The main difference: Mintlify uses hosted MDX with JSX components; Bengal uses self-hosted Markdown with directives.

| Mintlify | Bengal | Status |
|----------|--------|--------|
| `<Note>` | `:::{note}` | ✅ Direct equivalent |
| `<Warning>` | `:::{warning}` | ✅ Direct equivalent |
| `<Tip>` | `:::{tip}` | ✅ Direct equivalent |
| `<Info>` | `:::{info}` | ✅ Direct equivalent |
| `mint.json` | `bengal.toml` | ✅ Similar purpose |
| MDX files | Markdown files | ✅ Simpler |

---

## Component → Directive Translation

### Callouts / Admonitions

:::{tab-set}

:::{tab} Mintlify (MDX)
```jsx
<Note>
  This is a note callout in Mintlify.
</Note>

<Warning>
  This is a warning with important information.
</Warning>

<Tip>
  A helpful tip for your users.
</Tip>

<Info>
  Additional context or information.
</Info>
```
:::{/tab}

:::{tab} Bengal (No JSX!)
```markdown
:::{note}
This is a note callout in Bengal.
:::

:::{warning}
This is a warning with important information.
:::

:::{tip}
A helpful tip for your users.
:::

:::{info}
Additional context or information.
:::
```
:::{/tab}

:::{/tab-set}

:::{tip}
No imports, no JSX, no closing tags to match. Just clean markdown.
:::

### Cards and Card Groups

:::{tab-set}

:::{tab} Mintlify (MDX)
```jsx
<CardGroup cols={2}>
  <Card title="Quickstart" icon="rocket" href="/quickstart">
    Get started in under 5 minutes
  </Card>
  <Card title="API Reference" icon="code" href="/api-reference">
    Explore our API endpoints
  </Card>
  <Card title="SDKs" icon="cube" href="/sdks">
    Official client libraries
  </Card>
  <Card title="Examples" icon="lightbulb" href="/examples">
    Sample code and tutorials
  </Card>
</CardGroup>
```
:::{/tab}

:::{tab} Bengal (Built-in!)
```markdown
:::{cards}
:columns: 2

:::{card} Quickstart
:icon: rocket
:link: /quickstart/

Get started in under 5 minutes
:::{/card}

:::{card} API Reference
:icon: code
:link: /api-reference/

Explore our API endpoints
:::{/card}

:::{card} SDKs
:icon: cube
:link: /sdks/

Official client libraries
:::{/card}

:::{card} Examples
:icon: lightbulb
:link: /examples/

Sample code and tutorials
:::{/card}

:::{/cards}
```
:::{/tab}

:::{/tab-set}

### Tabs / Code Groups

:::{tab-set}

:::{tab} Mintlify (MDX)
````jsx
<Tabs>
  <Tab title="Python">
    ```python
    import requests
    response = requests.get("https://api.example.com/users")
    ```
  </Tab>
  <Tab title="JavaScript">
    ```javascript
    const response = await fetch("https://api.example.com/users");
    ```
  </Tab>
  <Tab title="cURL">
    ```bash
    curl https://api.example.com/users
    ```
  </Tab>
</Tabs>
````
:::{/tab}

:::{tab} Bengal (Cleaner!)
````markdown
:::{tab-set}
:::{tab} Python
```python
import requests
response = requests.get("https://api.example.com/users")
```
:::{/tab}
:::{tab} JavaScript
```javascript
const response = await fetch("https://api.example.com/users");
```
:::{/tab}
:::{tab} cURL
```bash
curl https://api.example.com/users
```
:::{/tab}
:::{/tab-set}
````
:::{/tab}

:::{/tab-set}

### Code Groups (Multi-file examples)

:::{tab-set}

:::{tab} Mintlify (MDX)
````jsx
<CodeGroup>
  ```python Python
  print("Hello, World!")
  ```

  ```javascript JavaScript
  console.log("Hello, World!");
  ```

  ```go Go
  fmt.Println("Hello, World!")
  ```
</CodeGroup>
````
:::{/tab}

:::{tab} Bengal
````markdown
:::{tab-set}
:::{tab} Python
```python
print("Hello, World!")
```
:::{/tab}
:::{tab} JavaScript
```javascript
console.log("Hello, World!");
```
:::{/tab}
:::{tab} Go
```go
fmt.Println("Hello, World!")
```
:::{/tab}
:::{/tab-set}
````
:::{/tab}

:::{/tab-set}

### Accordions

:::{tab-set}

:::{tab} Mintlify (MDX)
```jsx
<AccordionGroup>
  <Accordion title="What is your refund policy?">
    We offer a 30-day money-back guarantee on all plans.
  </Accordion>
  <Accordion title="How do I cancel my subscription?">
    You can cancel anytime from your account settings.
  </Accordion>
</AccordionGroup>
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{dropdown} What is your refund policy?
:icon: question

We offer a 30-day money-back guarantee on all plans.
:::

:::{dropdown} How do I cancel my subscription?
:icon: question

You can cancel anytime from your account settings.
:::
```
:::{/tab}

:::{/tab-set}

### Steps

:::{tab-set}

:::{tab} Mintlify (MDX)
```jsx
<Steps>
  <Step title="Install the SDK">
    ```bash
    pip install my-sdk
    ```
  </Step>
  <Step title="Initialize the client">
    ```python
    from my_sdk import Client
    client = Client(api_key="your-key")
    ```
  </Step>
  <Step title="Make your first request">
    ```python
    response = client.users.list()
    print(response)
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
pip install my-sdk
```
:::{/step}

:::{step} Initialize the client
```python
from my_sdk import Client
client = Client(api_key="your-key")
```
:::{/step}

:::{step} Make your first request
```python
response = client.users.list()
print(response)
```
:::{/step}

:::{/steps}
````
:::{/tab}

:::{/tab-set}

### API Reference Fields

:::{tab-set}

:::{tab} Mintlify (MDX)
```jsx
<ParamField path="user_id" type="string" required>
  The unique identifier of the user
</ParamField>

<ParamField body="email" type="string" required>
  User's email address
</ParamField>

<ResponseField name="id" type="string">
  Unique identifier for the created resource
</ResponseField>

<ResponseField name="created_at" type="string">
  ISO 8601 timestamp of creation
</ResponseField>
```
:::{/tab}

:::{tab} Bengal (Table format)
```markdown
## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | ✅ | The unique identifier of the user |
| `email` | string | ✅ | User's email address |

## Response

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the created resource |
| `created_at` | string | ISO 8601 timestamp of creation |
```
:::{/tab}

:::{/tab-set}

:::{note}
Bengal uses standard markdown tables for API parameters and responses. For complex API documentation, Bengal's autodoc can generate this from OpenAPI specs automatically.
:::

---

## Configuration Comparison

### Basic Config

:::{tab-set}

:::{tab} Mintlify (mint.json)
```json
{
  "name": "My API Docs",
  "logo": {
    "light": "/logo/light.svg",
    "dark": "/logo/dark.svg"
  },
  "favicon": "/favicon.png",
  "colors": {
    "primary": "#0D9373",
    "light": "#07C983",
    "dark": "#0D9373"
  },
  "topbarLinks": [
    {
      "name": "Dashboard",
      "url": "https://dashboard.example.com"
    }
  ],
  "topbarCtaButton": {
    "name": "Get API Key",
    "url": "https://dashboard.example.com/api-keys"
  },
  "navigation": [
    {
      "group": "Getting Started",
      "pages": ["introduction", "quickstart", "authentication"]
    },
    {
      "group": "API Reference",
      "pages": ["api-reference/users", "api-reference/orders"]
    }
  ],
  "api": {
    "baseUrl": "https://api.example.com"
  }
}
```
:::{/tab}

:::{tab} Bengal (bengal.toml)
```toml
[site]
title = "My API Docs"
baseurl = "https://docs.example.com"
theme = "bengal"

[site.logo]
light = "logo/light.svg"
dark = "logo/dark.svg"

# Navigation is auto-generated from directory structure
# Use weight frontmatter for ordering

# OpenAPI integration
[autodoc.openapi]
enabled = true
spec = "openapi.yaml"
output_prefix = "api-reference"
```
:::{/tab}

:::{/tab-set}

### Navigation

:::{tab-set}

:::{tab} Mintlify (mint.json)
```json
{
  "navigation": [
    {
      "group": "Getting Started",
      "pages": [
        "introduction",
        "quickstart",
        "authentication"
      ]
    },
    {
      "group": "Guides",
      "pages": [
        "guides/webhooks",
        "guides/pagination",
        "guides/errors"
      ]
    }
  ]
}
```
:::{/tab}

:::{tab} Bengal (Directory + Frontmatter)
```markdown
<!-- Auto-generated from structure: -->
content/
├── docs/
│   ├── getting-started/
│   │   ├── _index.md (weight: 10)
│   │   ├── introduction.md (weight: 10)
│   │   ├── quickstart.md (weight: 20)
│   │   └── authentication.md (weight: 30)
│   └── guides/
│       ├── _index.md (weight: 20)
│       ├── webhooks.md (weight: 10)
│       ├── pagination.md (weight: 20)
│       └── errors.md (weight: 30)

<!-- Example _index.md -->
---
title: Getting Started
weight: 10
---
```
:::{/tab}

:::{/tab-set}

:::{tip}
No `mint.json` navigation updates needed! Add a page, and it appears in nav automatically. Use `weight` frontmatter to control order.
:::

---

## What You Don't Need Anymore

| Mintlify Requires | Bengal |
|-------------------|--------|
| Hosted platform subscription | Self-hosted (free) |
| `mint.json` navigation updates | Auto-generated from directories |
| JSX/MDX knowledge | Just Markdown |
| Component imports | Built-in directives |
| Mintlify CLI | `bengal` CLI |
| GitHub App integration | Standard Git workflow |
| Platform-specific features | Open source, extensible |

---

## Feature Comparison

### What Bengal Has (Self-Hosted Equivalent)

| Feature | Mintlify | Bengal |
|---------|----------|--------|
| Callouts | `<Note>`, `<Warning>` | `:::{note}`, `:::{warning}` ✅ |
| Tabs | `<Tabs>` | `:::{tab-set}` ✅ |
| Cards | `<Card>`, `<CardGroup>` | `:::{cards}` ✅ |
| Steps | `<Steps>` | `:::{steps}` ✅ |
| Accordions | `<Accordion>` | `:::{dropdown}` ✅ |
| Code blocks | Built-in | Built-in ✅ |
| OpenAPI | Built-in | `:::{openapi}` or autodoc ✅ |
| Search | Hosted | Built-in index ✅ |
| Analytics | Built-in | Integrate any provider |
| Dark mode | Built-in | Built-in ✅ |
| Versioning | Limited | `_versions/` folders ✅ |

### What's Different (Trade-offs)

| Feature | Mintlify | Bengal | Trade-off |
|---------|----------|--------|-----------|
| Hosting | Managed | Self-hosted | More control, more responsibility |
| API playground | Interactive | Static | No runtime, use external tools |
| Feedback widget | Built-in | Custom integration | More flexible |
| User auth | Built-in | External | Integrate your own |
| Changelog | Built-in component | Standard pages | Simpler |
| AI features | Built-in | External | Use your own AI tools |

---

## OpenAPI Integration

### Mintlify Approach

```json
// mint.json
{
  "openapi": "openapi.yaml",
  "api": {
    "baseUrl": "https://api.example.com"
  }
}
```

### Bengal Approach

```yaml
# config/_default/autodoc.yaml
autodoc:
  openapi:
    enabled: true
    specs:
      - path: "openapi.yaml"
        output_prefix: "api-reference"
        generate_pages: true
```

Or inline in markdown:

```markdown
:::{openapi} openapi.yaml
:path: /users
:method: GET
:::
```

---

## Directory Structure Comparison

| Mintlify | Bengal | Notes |
|----------|--------|-------|
| `docs/` root | `content/` | Content location |
| `mint.json` | `bengal.toml` | Configuration |
| `openapi.yaml` | `openapi.yaml` | Same location works |
| `images/` | `assets/` | Static files |
| `api-reference/` | `content/docs/api-reference/` | API docs |
| `snippets/` | `content/_snippets/` | Reusable content |

---

## What Bengal Adds

:::::{tab-set}

::::{tab} Content Reuse
```markdown
<!-- Define once in _snippets/auth-header.md -->
Add your API key to the Authorization header:
`Authorization: Bearer YOUR_API_KEY`

<!-- Reuse anywhere -->
:::{include} /_snippets/auth-header.md
:::
```

Mintlify has snippets too, but Bengal's are more flexible with filtering.
::::{/tab}

::::{tab} Variables
```markdown
---
title: API Reference
api_version: "2.0"
base_url: "https://api.example.com/v2"
---

# {{ page.title }}

Current API version: **{{ page.metadata.api_version }}**

Base URL: `{{ page.metadata.base_url }}`
```

Use variables directly in markdown without JSX.
::::{/tab}

::::{tab} Build-time Validation
```bash
# Validate all links work
bengal health linkcheck

# Check for broken references  
bengal health

# Full site analysis
bengal analyze
```

Catch issues before deployment, not after.
::::{/tab}

::::{tab} Local Development
```bash
# Fast local dev server with hot reload
bengal serve

# Build for production
bengal build

# No cloud dependency for preview
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
# Copy your Mintlify MDX files
cp -r /path/to/mintlify/docs/* content/docs/

# Files will need conversion (see next steps)
```
:::{/step}

:::{step} Convert MDX to Markdown
Replace JSX components with directives:

| Find | Replace With |
|------|--------------|
| `<Note>` ... `</Note>` | `:::{note}` ... `:::` |
| `<Warning>` ... `</Warning>` | `:::{warning}` ... `:::` |
| `<Tabs>` | `:::{tab-set}` |
| `<Tab title="X">` | `:::{tab} X` |
| `<Card title="X">` | `:::{card} X` |
| `<CardGroup>` | `:::{cards}` |
| `<Steps>` | `:::{steps}` |
| `<Accordion>` | `:::{dropdown}` |
:::{/step}

:::{step} Add Frontmatter
Add ordering to pages that need it:

```yaml
---
title: Quickstart
weight: 20
---
```
:::{/step}

:::{step} Update Config
Create `bengal.toml` based on your `mint.json`:

```toml
[site]
title = "My API Docs"
baseurl = "https://docs.example.com"
theme = "bengal"
```
:::{/step}

:::{step} Copy Assets
```bash
cp -r /path/to/mintlify/images/* assets/
cp /path/to/mintlify/openapi.yaml .
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
- [ ] Export/backup your Mintlify content
- [ ] Create new Bengal site: `bengal new site mysite`
:::

:::{checklist} Content Migration
- [ ] Copy MDX files to `content/docs/`
- [ ] Convert `<Note>` to `:::{note}`
- [ ] Convert `<Tabs>` to `:::{tab-set}`
- [ ] Convert `<Card>` to `:::{card}`
- [ ] Convert `<Steps>` to `:::{steps}`
- [ ] Convert `<Accordion>` to `:::{dropdown}`
- [ ] Remove JSX imports and exports
:::

:::{checklist} Configuration
- [ ] Create `bengal.toml` from `mint.json`
- [ ] Add `weight` frontmatter for ordering
- [ ] Configure OpenAPI integration if used
:::

:::{checklist} Assets
- [ ] Copy images to `assets/`
- [ ] Update image paths in content
- [ ] Copy OpenAPI spec if used
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | Mintlify | Bengal |
|------|----------|--------|
| Install | `npm i mintlify` | `pip install bengal` |
| New site | Dashboard | `bengal new site` |
| Build | `mintlify build` | `bengal build` |
| Serve | `mintlify dev` | `bengal serve` |
| Deploy | Push to repo | Any static host |
| Note | `<Note>` | `:::{note}` |
| Tabs | `<Tabs>` | `:::{tab-set}` |
| Cards | `<CardGroup>` | `:::{cards}` |
| Steps | `<Steps>` | `:::{steps}` |

---

## Common Questions

:::{dropdown} Why leave Mintlify?
:icon: question

Common reasons for migration:
- **Cost**: Self-hosted Bengal is free
- **Control**: Own your infrastructure and data
- **Customization**: Full source access for theming
- **No vendor lock-in**: Standard markdown, deploy anywhere
- **Offline development**: Full local workflow
:::

:::{dropdown} What about the API playground?
:icon: question

Mintlify's interactive API playground doesn't have a direct Bengal equivalent. Options:
- Link to external tools (Postman, Insomnia)
- Embed Swagger UI
- Use static code examples (often clearer anyway)
- Build a custom solution
:::

:::{dropdown} Can I keep my OpenAPI integration?
:icon: question

Yes! Bengal supports OpenAPI specs:

```yaml
# config/_default/autodoc.yaml
autodoc:
  openapi:
    enabled: true
    specs:
      - path: "openapi.yaml"
        output_prefix: "api"
```

Or reference inline:

```markdown
:::{openapi} openapi.yaml
:path: /users
:method: POST
:::
```
:::

:::{dropdown} What about analytics and feedback?
:icon: question

Integrate any analytics provider you prefer:
- Google Analytics
- Plausible
- Fathom
- PostHog

Add the script to your theme's base template. You have full control.
:::

:::{dropdown} How do I handle authentication/gating?
:icon: question

Bengal generates static HTML. For protected docs:
- Use your hosting platform's auth (Netlify, Vercel)
- Deploy behind a reverse proxy
- Build a custom solution
- Consider Bengal for public docs, separate tool for private
:::

---

## Next Steps

- [Directives Reference](/docs/reference/directives/) - All available directives
- [Writer Quickstart](/docs/get-started/quickstart-writer/) - Full markdown guide
- [Configuration Reference](/docs/building/configuration/) - Config options
- [OpenAPI Autodoc](/docs/content/sources/autodoc/) - API doc generation
