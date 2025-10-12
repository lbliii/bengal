# Structured Content Architecture - Feature Analysis

**Date:** October 12, 2025  
**Status:** 🤔 Analysis & Planning Phase

## What Are We Really Building?

After implementing site templates and the data-driven resume, let's step back and understand what this feature set actually is.

## Current State: Bengal's Content Model

Bengal currently has a **three-layer content model**:

```
┌─────────────────────────────────────┐
│   PRESENTATION LAYER                │
│   - Templates (Jinja2)              │
│   - Themes                          │
│   - Components                      │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   CONTENT LAYER                     │
│   - Pages (markdown + frontmatter) │
│   - Sections (hierarchical)         │
│   - Content Types (page/post/doc)  │
│   - Taxonomies (tags/categories)    │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   DATA LAYER (partial)              │
│   - page.metadata (frontmatter)     │
│   - get_data() function             │
│   - site.config                     │
└─────────────────────────────────────┘
```

**What's Missing:** A complete **Structured Content Layer** between content and data.

## The Gap We Discovered

### Problem 1: Content vs Data Blur

When building a resume, we hit a conceptual issue:

```yaml
---
title: Resume
# Is this "content" or "data"?
experience:
  - title: Senior Engineer
    company: Tech Co
    highlights: [...]  # 100 lines of structured data
education: [...]      # 50 lines more
skills: [...]         # 30 lines more
# Total: 200+ lines of YAML in frontmatter
---

# And maybe 5 lines of actual prose content here?
```

**Question:** Is this a "page with lots of metadata" or "structured data with a template"?

### Problem 2: Reusability

```yaml
# Team page needs:
team:
  - name: Alice
    role: CEO
  - name: Bob
    role: CTO

# About page also needs team data
# Products page needs team contact info
# How do we share this data?
```

Currently: Copy-paste or use `get_data()` function.
Missing: Automatic availability like Hugo's `site.data`

### Problem 3: Content Type Confusion

```
content/
├── pages/           ← Prose content (blog posts, articles)
├── data-pages/      ← Structured content (resumes, team)  
└── data/            ← Pure data (no templates)

Where does each type of content belong?
```

## What This Feature Set Is Called

After analysis, this is a **Structured Content System** or **Data-Driven Content Architecture**.

### Industry Terms

Different SSGs call it different things:

| SSG | Term | Concept |
|-----|------|---------|
| **Hugo** | "Data Templates" | Templates + data/ directory |
| **Jekyll** | "Data Files" | YAML/JSON in _data/ |
| **11ty** | "Global Data" | JavaScript data files |
| **Gatsby** | "Data Layer" | GraphQL over everything |
| **Contentful** | "Structured Content" | Content models + data |

### What Bengal Should Call It

**Proposed:** **Structured Content System**

Components:
1. **Content Models** - Define data structures (resume, team, product)
2. **Data Sources** - Where data comes from (frontmatter, data/, APIs)
3. **Template Binding** - How templates consume structured data
4. **Data Access Patterns** - How to access data (site.data, get_data)

## User Personas & Use Cases

### Persona 1: The Writer (Content Creator)

**Who:** Non-technical user creating content

**Needs:**
- Simple, obvious structure
- Clear examples
- Minimal YAML syntax
- Separation of concerns

**Use Cases:**

#### UC1: Simple Blog Post (Current - Works Great)
```yaml
---
title: My Post
date: 2025-10-12
tags: [python, tutorial]
---

# My Post

Content here...
```

**Experience:** ✅ Great - Clear separation, minimal metadata

#### UC2: Resume/CV (Current - Awkward)
```yaml
---
title: Resume
name: John Doe
experience: [... 100 lines ...]
education: [... 50 lines ...]
---

Optional bio text here.
```

**Experience:** 🟡 Awkward - Too much YAML, hard to edit, unclear what's content vs data

#### UC3: Resume/CV (With Structured Content System)

**Option A: External Data File**
```yaml
# content/resume/index.md (minimal)
---
title: Resume
data_file: resume.yaml  # Reference to data
---

Optional bio text here.
```

```yaml
# data/resume.yaml (structured data)
name: John Doe
experience: [...]
education: [...]
```

**Experience:** ✅ Better - Clear separation, easier to edit

**Option B: Automatic Data Loading**
```yaml
# content/resume.md (minimal)
---
title: Resume
---

Optional bio text here.
```

```yaml
# data/resume.yaml (auto-loaded by name)
name: John Doe
experience: [...]
```

```jinja2
{# template automatically gets site.data.resume #}
{{ site.data.resume.name }}
```

**Experience:** ✅ Best - Convention over configuration

### Persona 2: The Theme Developer

**Who:** Developer creating reusable themes

**Needs:**
- Flexible data access
- Clear APIs
- Type safety (or at least predictability)
- Performance

**Use Cases:**

#### UC1: Team Page Template (Current)
```jinja2
{# templates/team.html #}
{# How do I get team data? Multiple ways, confusing #}

{# Option 1: From page frontmatter #}
{% for member in page.metadata.team %}
  {{ member.name }}
{% endfor %}

{# Option 2: Load external file #}
{% set team = get_data('data/team.yaml') %}
{% for member in team %}
  {{ member.name }}
{% endfor %}

{# Option 3: ??? #}
```

**Experience:** 🟡 Confusing - No clear pattern, theme doesn't know where data comes from

#### UC2: Team Page Template (With Structured Content System)
```jinja2
{# templates/team.html #}
{# Clear, predictable API #}

{# Convention: team data always in site.data.team #}
{% for member in site.data.team %}
  <div class="member">
    <h3>{{ member.name }}</h3>
    <p>{{ member.role }}</p>
  </div>
{% endfor %}

{# Or if page-specific #}
{% for member in page.data.team %}
  ...
{% endfor %}
```

**Experience:** ✅ Clear - Predictable patterns, documented conventions

#### UC3: Flexible Resume Template (Theme Developer Goal)
```jinja2
{# templates/resume/single.html #}
{# Works with data from multiple sources #}

{# Try page-local data first #}
{% set resume = page.data.resume or site.data.resume or {} %}

{# Or explicit #}
{% if page.metadata.data_source %}
  {% set resume = site.data[page.metadata.data_source] %}
{% else %}
  {% set resume = page.metadata %}
{% endif %}

<h1>{{ resume.name }}</h1>

{% for job in resume.experience %}
  <div class="job">
    <h3>{{ job.title }}</h3>
    <p>{{ job.company }}</p>
  </div>
{% endfor %}
```

**Experience:** ✅ Flexible - Theme works regardless of data source

### Persona 3: The Technical Writer (Documentation)

**Who:** Technical writer creating docs site

**Needs:**
- Structured data for API docs
- Reusable content snippets
- Version-specific data
- Consistency

**Use Cases:**

#### UC1: API Reference with Version Data
```yaml
# data/api/v2.yaml
version: "2.0"
endpoints:
  - path: /users
    method: GET
    description: List users
    parameters: [...]
```

```jinja2
{# templates/api-reference.html #}
{% for endpoint in site.data.api.v2.endpoints %}
  <div class="endpoint">
    <code>{{ endpoint.method }} {{ endpoint.path }}</code>
    <p>{{ endpoint.description }}</p>
  </div>
{% endfor %}
```

**Experience:** ✅ Great - Structured API data, easy to maintain

#### UC2: Reusable Code Examples
```yaml
# data/examples/python.yaml
basic_usage: |
  import bengal
  site = bengal.Site.from_config('.')
  site.build()

advanced_usage: |
  # Advanced example
  ...
```

```jinja2
{# In any template #}
```python
{{ site.data.examples.python.basic_usage }}
```
```

**Experience:** ✅ Great - DRY, consistent examples across docs

## Conceptual Model

### Three Types of Content

```
1. PROSE CONTENT (Traditional)
   ├─ Blog posts
   ├─ Articles
   └─ Documentation pages

   Characteristics:
   - Mostly markdown text
   - Minimal metadata
   - Linear reading
   - Template: prose + sidebar/chrome

2. STRUCTURED CONTENT (New Focus)
   ├─ Resumes/CVs
   ├─ Team pages
   ├─ Product catalogs
   ├─ Event listings
   └─ API references

   Characteristics:
   - Mostly structured data (YAML/JSON)
   - Minimal prose
   - Non-linear, scannable
   - Template: data → layout

3. PURE DATA (Existing, improve)
   ├─ Configuration
   ├─ Translations
   ├─ Shared datasets
   └─ Theme data

   Characteristics:
   - 100% data, no content
   - Reused across pages
   - Not a "page" itself
   - Accessed via site.data
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────┐
│  SOURCES                                        │
├─────────────────────────────────────────────────┤
│  1. Frontmatter (page.metadata)                 │
│  2. Data Directory (data/*.yaml)                │
│  3. Page Data (content/*/data.yaml)             │
│  4. External APIs (future)                      │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼───────┐
         │  DATA LAYER   │
         │               │
         │  Normalized   │
         │  Cached       │
         │  Typed        │
         └───────┬───────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│ page  │   │ site  │   │ get   │
│ .data │   │ .data │   │ _data │
└───┬───┘   └───┬───┘   └───┬───┘
    │           │           │
    └───────────┼───────────┘
                │
        ┌───────▼────────┐
        │   TEMPLATES    │
        │                │
        │   Render data  │
        │   to HTML      │
        └────────────────┘
```

## Proposed Feature Name

### Option 1: "Structured Content System" ⭐ (Recommended)
**Why:**
- Industry standard term
- Describes what it does
- Familiar to Headless CMS users
- Broad enough to encompass all use cases

### Option 2: "Data-Driven Pages"
**Why:** Clear and descriptive
**Against:** Sounds like a feature, not a system

### Option 3: "Content Models"
**Why:** Familiar from CMSs
**Against:** Implies schema/validation we don't have yet

### Option 4: "Data Templates"
**Why:** What Hugo calls it
**Against:** Focuses on templates, not the data

## Feature Set Breakdown

### Core Features (MVP)

1. **`site.data` Object** (Hugo-inspired)
   - Auto-loads `data/` directory
   - Nested directory support
   - Clean dot notation access
   - Cached for performance

2. **DotDict Wrapper**
   - Avoid Jinja2 `.items` gotcha
   - Clean field access
   - Better error messages

3. **Data Directory Convention**
   ```
   data/
   ├── team.yaml          # site.data.team
   ├── products.yaml      # site.data.products
   └── api/
       ├── v1.yaml        # site.data.api.v1
       └── v2.yaml        # site.data.api.v2
   ```

4. **Template Patterns**
   - Document `site.data` vs `page.metadata`
   - Show when to use each
   - Provide clear examples

### Extended Features (Phase 2)

5. **Page-Local Data**
   ```
   content/
   └── team/
       ├── index.md       # Team page
       └── data.yaml      # page.data.team (page-local)
   ```

6. **Data Preprocessing**
   - Computed fields
   - Data validation
   - Transform hooks

7. **Schema Validation** (Optional)
   ```yaml
   # data/team.yaml
   # schema: team  # References schemas/team.json
   members:
     - name: Alice
       role: CEO
   ```

8. **Multi-Source Data**
   - Merge data from multiple sources
   - Override by environment
   - Data inheritance

## Documentation Structure

### For Writers

**Guide:** "Working with Structured Content"

Sections:
1. When to use structured content
2. Simple examples (team page, product catalog)
3. Frontmatter vs data files
4. Editing YAML tips
5. Common patterns

### For Theme Developers

**Guide:** "Building Data-Driven Themes"

Sections:
1. Accessing data (site.data, page.data, get_data)
2. Template patterns
3. Defensive coding
4. Performance considerations
5. Jinja2 gotchas

### For Technical Writers

**Guide:** "Documentation with Structured Data"

Sections:
1. API reference patterns
2. Version-specific data
3. Reusable examples
4. Multi-page consistency
5. Automation tips

## Success Metrics

How do we know if this is successful?

### For Writers
- ✅ Can create resume without confusion
- ✅ Understands when to use data files
- ✅ Can maintain team page easily
- ✅ Doesn't need to understand templates

### For Theme Developers
- ✅ Clear API for accessing data
- ✅ Predictable patterns
- ✅ Good performance (caching)
- ✅ Comprehensive examples

### For Technical Writers
- ✅ Can structure API docs with data
- ✅ Can maintain consistency
- ✅ Can automate repetitive content
- ✅ Can version documentation data

## Next Actions

1. **Naming Decision** - Agree on "Structured Content System"
2. **Core Implementation** - site.data + DotDict (~4 hours)
3. **Documentation** - Three user guides (~6 hours)
4. **Examples** - Real-world templates (~4 hours)
5. **Testing** - Validate with real users

## Open Questions

1. **Should `page.data` exist separately from `page.metadata`?**
   - Pro: Clear separation of concerns
   - Con: More complexity, two places to look

2. **Should we support data in content/ directories?**
   ```
   content/team/data.yaml  # Page-local data
   ```
   - Pro: Keeps related data together
   - Con: Blurs content/data boundary

3. **Should we have schema validation?**
   - Pro: Catch errors early, better DX
   - Con: Added complexity, maintenance

4. **Should we support external APIs?**
   ```yaml
   # data/github.yaml
   source: https://api.github.com/repos/user/repo
   cache: 1h
   ```
   - Pro: Dynamic data, powerful
   - Con: Build-time dependencies, security

## Conclusion

**What is this feature set?**

A **Structured Content System** that enables:
1. Separation of data from prose
2. Reusable data across pages
3. Data-driven templates
4. Clear patterns for writers and developers

**Who benefits?**
- **Writers:** Clearer mental model, easier editing
- **Theme Developers:** Predictable APIs, better templates
- **Technical Writers:** Structured docs, consistency

**Priority:** High - This is a fundamental expansion of Bengal's content model.
