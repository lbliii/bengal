---
title: Specialized Site Scenarios
nav_title: Specialized Scenarios
description: i18n, landing pages, resume, and changelog site patterns
weight: 101
tags:
- persona-writer
- persona-operator
---

# Specialized Site Scenarios

Patterns for i18n, marketing landing pages, resume/CV sites, and changelogs.

:::{note}
**Do I need this?** Use when your site type is not covered in
[[docs/tutorials/user-scenarios|User Scenarios]] (blog, docs, portfolio, mixed,
multi-variant). For a faster first run, start with
[[docs/get-started/quickstart-writer|Writer Quickstart]].
:::
## Multi-Language Site {#international-site}

Create content in multiple languages using directory-based structure.

**What you'll get**: A multilingual site with language-specific content directories, SEO-friendly hreflang tags, and language switcher support.

### Content Organization

Bengal supports directory-based i18n for content organization:

```tree
content/
├── en/
│   ├── _index.md       # lang: en
│   ├── about.md
│   └── docs/
│       └── guide.md
└── fr/
    ├── _index.md       # lang: fr
    ├── about.md
    └── docs/
        └── guide.md
```

### Configuration

In `bengal.toml` or `config/_default/i18n.yaml`:

```yaml
i18n:
  default_language: en
  content_structure: dir
  languages:
    - code: en
      name: English
      weight: 1
    - code: fr
      name: Français
      weight: 2
```

### Template Functions

Use these in templates for language switching:

- `languages()` - Get list of configured languages
- `alternate_links(page)` - Generate hreflang tags for SEO (takes optional page parameter)

### Limitations

- UI translation (strings) requires separate i18n YAML files
- See [[docs/build-sites/structure/i18n|i18n documentation]] for full details

---

## Landing Page {#landing-page}

Build a marketing or product landing page.

**What you'll get**: A single-page marketing site with hero section, feature highlights, and call-to-action elements.

### 1. Scaffold Landing

```bash
bengal new site mylanding --template landing
cd mylanding
```

### 2. Customize Hero Section

Edit `content/index.md`:

```markdown
---
title: "Welcome to MyProduct"
type: landing
layout: landing
hero:
  title: "Build Faster"
  subtitle: "The modern way to create static sites"
  cta:
    text: "Get Started"
    url: "/docs/getting-started/"
---
```

### 3. Add Sections

Use shortcodes and directives for landing page sections:

```markdown
:::{features}
- title: Fast
  icon: rocket
  description: Builds in seconds

- title: Flexible
  icon: puzzle
  description: Customize everything
:::
```

---

## Resume/CV Site {#resume-site}

Build a professional resume or CV site.

**What you'll get**: A professional resume site with structured data for experience, education, and contact information.

### 1. Scaffold Resume

```bash
bengal new site myresume --template resume
cd myresume
```

### 2. Edit Resume Data

Update `data/resume.yaml` with your information:

```yaml
name: "Jane Developer"
title: "Senior Software Engineer"
contact:
  email: "jane@example.com"
  github: "janedeveloper"
  linkedin: "in/janedeveloper"

experience:
  - title: "Senior Engineer"
    company: "Tech Corp"
    dates: "2022 - Present"
    description: "Led development of..."

education:
  - degree: "B.S. Computer Science"
    school: "University"
    year: 2018
```

---

## Changelog Site {#changelog-site}

Maintain a project changelog with releases.

**What you'll get**: A changelog site with versioned releases, categorized changes (added, fixed, changed), and chronological organization.

### 1. Scaffold Changelog

```bash
bengal new site mychangelog --template changelog
cd mychangelog
```

### 2. Add Releases

Update `data/changelog.yaml`:

```yaml
releases:
  - version: "1.2.0"
    date: 2025-06-15
    changes:
      - type: added
        description: "New feature X"
      - type: fixed
        description: "Bug in Y"
      - type: changed
        description: "Updated Z"

  - version: "1.1.0"
    date: 2025-05-01
    changes:
      - type: added
        description: "Initial feature set"
```

---

## Next Steps

- See [[docs/reference/site-templates|Templates Reference]] for template details
- Read [[docs/build-sites/structure/i18n|Internationalization]] for full i18n workflows
- Explore [[docs/build-sites/customize|Theming]] for customization
