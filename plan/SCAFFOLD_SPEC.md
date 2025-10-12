# Bengal Site Initialization (Init) Specification

**Status**: Draft  
**Created**: 2025-10-12  
**Owner**: Bengal Core Team

## Overview

Site initialization provides a quick way to bootstrap a new Bengal site with a predefined structure. Instead of manually creating directories and files, users can generate a complete site skeleton in seconds using `bengal init`.

## Goals

1. **Speed**: Go from idea to working site in under 60 seconds
2. **Simplicity**: Simple CLI commands for common patterns
3. **Flexibility**: Support both simple and complex structures
4. **Education**: Generated files serve as examples for new users
5. **Customization**: Easy to modify after generation

## Non-Goals

- Real-time content generation (that's content adapters)
- Site migration (that's import/migration features)
- Theme generation (themes are separate)

## User Stories

### Story 1: First-Time User (Wizard)
```bash
$ bengal new my-site

✨ Created new Bengal site: my-site

Initialize site structure? (Y/n):
> What kind of site are you building?
  1. 📝 Blog
  2. 📚 Documentation
  3. 💼 Portfolio
  4. 🏢 Business
  5. ⚙️  Custom

Selection [1]: 3

> Generate sample content? (Y/n): y
> Pages per section? [3]:

Creating portfolio structure...
✓ Created about/ (3 pages)
✓ Created projects/ (3 pages)  
✓ Created blog/ (3 pages)
✓ Created contact/ (1 page)

✨ All done! Run 'bengal serve' to preview your site.
```

### Story 2: Quick Command Line
```bash
bengal new my-site
cd my-site
bengal init --sections "about,blog,projects,contact"
bengal serve
```

### Story 3: Documentation Site with Preset
```bash
bengal new docs-site
cd docs-site
bengal init --preset docs
bengal serve
```

### Story 4: Custom Structure from Schema
```bash
bengal new portfolio
cd portfolio
bengal init --from structure.yaml
bengal serve
```

## Command Interface

### Primary Command

```bash
bengal init [OPTIONS]
```

### Options

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--sections` | string | Comma-separated section names | `--sections "blog,projects"` |
| `--preset` | string | Use a preset structure | `--preset docs` |
| `--from` | path | Load structure from YAML/JSON | `--from structure.yaml` |
| `--with-content` | bool | Generate sample content | `--with-content` |
| `--pages-per-section` | int | Number of sample pages per section | `--pages-per-section 3` |
| `--force` | bool | Overwrite existing content | `--force` |
| `--dry-run` | bool | Show what would be created | `--dry-run` |
| `--interactive` | bool | Interactive prompts | `--interactive` |

### Option Precedence

If multiple options provided:
1. `--from` (highest priority - explicit schema)
2. `--preset` (medium priority - named template)
3. `--sections` (lowest priority - simple list)

## Generated Structure

### Minimal Init (`--sections "blog"`)

```
content/
  blog/
    _index.md           # Section index
    hello-world.md      # Sample post (if --with-content)
```

### Full Init (`--sections "about,blog,projects" --with-content`)

```
content/
  about/
    _index.md
    team.md
    history.md
  blog/
    _index.md
    first-post.md
    second-post.md
    third-post.md
  projects/
    _index.md
    project-alpha.md
    project-beta.md
    project-gamma.md
```

## File Templates

### Section Index (`_index.md`)

```markdown
---
title: {Section Title}
description: {Auto-generated description}
type: section
weight: {auto-incremented}
---

# {Section Title}

This is the {section} section. Add your content here.

<!-- TODO: Customize this section -->
```

### Sample Page

```markdown
---
title: {Page Title}
date: {current date}
draft: false
description: {Auto-generated description}
tags: [sample, generated]
---

# {Page Title}

This is a sample page in the {section} section.

## Getting Started

Replace this content with your own.

<!-- TODO: Replace this sample content -->
```

## Presets

Built-in structure templates for common use cases.

### `docs` Preset

```yaml
sections:
  - name: getting-started
    pages:
      - quickstart
      - installation
      - configuration
  - name: guides
    pages:
      - basic-usage
      - advanced-features
  - name: reference
    pages:
      - api
      - cli
  - name: community
    pages:
      - contributing
      - support
```

### `blog` Preset

```yaml
sections:
  - name: blog
    pages:
      - welcome
      - about-this-blog
  - name: about
    pages:
      - me
```

### `portfolio` Preset

```yaml
sections:
  - name: about
    pages:
      - bio
      - resume
  - name: projects
    pages:
      - project-1
      - project-2
      - project-3
  - name: contact
    pages:
      - get-in-touch
```

### `business` Preset

```yaml
sections:
  - name: products
    pages:
      - product-a
      - product-b
  - name: services
    pages:
      - consulting
      - support
  - name: about
    pages:
      - team
      - company
  - name: contact
    pages:
      - sales
```

## Schema Format

For `--from structure.yaml` option.

### Simple Schema

```yaml
# structure.yaml
sections:
  - about
  - blog
  - projects
  - contact
```

### Detailed Schema

```yaml
# structure.yaml
site:
  title: "My Portfolio"
  description: "A showcase of my work"

sections:
  - name: about
    title: "About Me"
    description: "Learn more about me"
    weight: 10
    pages:
      - name: bio
        title: "Biography"
        template: basic
      - name: resume
        title: "My Resume"
        template: basic

  - name: blog
    title: "Blog"
    description: "My thoughts and writings"
    weight: 20
    type: collection  # Indicates this is a content collection
    sample_count: 5   # Generate 5 sample posts
    pages:
      - name: welcome
        title: "Welcome to my blog"
        pinned: true

  - name: projects
    title: "Projects"
    weight: 30
    pages:
      - name: project-alpha
        title: "Project Alpha"
        frontmatter:
          tags: [python, web]
          status: active
      - name: project-beta
        title: "Project Beta"
        frontmatter:
          tags: [javascript, react]
          status: complete
```

### Schema with Templates

```yaml
# structure.yaml
templates:
  project_page:
    frontmatter:
      layout: project
      tags: [project]
    content: |
      # {title}

      ## Overview

      <!-- Describe the project -->

      ## Technologies

      - Technology 1
      - Technology 2

      ## Links

      - [GitHub](#)
      - [Demo](#)

sections:
  - name: projects
    pages:
      - name: my-project
        title: "My Awesome Project"
        template: project_page
```

## Wizard Experience

### Design Principles

The wizard is designed for **first-time success**:

1. **Default to Yes**: Most users want structure, so default answer is 'Y'
2. **Progressive Disclosure**: Start simple, offer more options as needed
3. **Preview Before Commit**: Show what will be created before creating it
4. **Smart Defaults**: Reasonable defaults for all prompts
5. **Escape Hatches**: Easy to skip (`--no-init`) or run later
6. **Visual Feedback**: Use emojis and formatting for clarity
7. **Helpful Context**: Brief explanations for each choice

### Integrated with `bengal new`

The recommended flow makes initialization part of site creation:

```bash
$ bengal new my-site

✨ Created new Bengal site: my-site

Initialize site structure? (Y/n): y

> What kind of site are you building?
  1. 📝 Blog           - Personal or professional blog
  2. 📚 Documentation  - Technical docs or guides  
  3. 💼 Portfolio      - Showcase your work
  4. 🏢 Business       - Company or product site
  5. ⚙️  Custom        - Define your own structure

Selection [1]: 3

> Generate sample content? (Y/n): y
  Sample content helps you see how pages are structured

> How many sample pages per section? [3]:

Preview of structure:
  content/
    about/
      _index.md
      bio.md
      resume.md
      skills.md
    projects/
      _index.md
      project-alpha.md
      project-beta.md
      project-gamma.md
    blog/
      _index.md
      welcome-post.md
      second-post.md
      third-post.md
    contact/
      _index.md
      get-in-touch.md

Create this structure? (Y/n): y

Creating structure...
✓ Created about/ (4 pages)
✓ Created projects/ (4 pages)
✓ Created blog/ (4 pages)
✓ Created contact/ (2 pages)

✨ All done!

Next steps:
  cd my-site
  bengal serve      # Preview your site

Your site is ready at http://localhost:5000
```

### Standalone Interactive Mode

Can also be run separately:

```bash
$ cd existing-site
$ bengal init --interactive

> What kind of site are you building?
  ...
```

### Skip Wizard

Users can skip the wizard in multiple ways:

```bash
# Skip during creation
$ bengal new my-site --no-init

# Or just press 'n' at the prompt
$ bengal new my-site
Initialize site structure? (Y/n): n

✨ Created empty Bengal site: my-site
Run 'bengal init' anytime to add structure
```

## Smart Defaults

### Section Titles
- `blog` → "Blog"
- `about` → "About"
- `getting-started` → "Getting Started"
- `api-reference` → "API Reference"

### Sample Content Variations

For blogs:
- "Welcome to {site title}"
- "Getting Started with {section}"
- "Tips and Tricks"

For docs:
- "Introduction"
- "Quick Start"
- "Installation"

For projects:
- "Project Alpha"
- "Project Beta"
- "Project Gamma"

### Weights
Auto-increment by 10 for easy reordering:
- First section: weight 10
- Second section: weight 20
- Third section: weight 30

## Sample Content Generation

### `--with-content` Behavior

Generates realistic placeholder content using templates:

```markdown
---
title: Welcome to Our Blog
date: 2025-10-12
draft: false
description: An introduction to our blog and what to expect
tags: [welcome, introduction]
---

# Welcome to Our Blog

Welcome! This is a sample blog post to help you get started.

## What This Blog Is About

This blog will cover topics related to:

- Topic area 1
- Topic area 2
- Topic area 3

## What's Next

Stay tuned for more posts coming soon!

<!-- TODO: Replace this sample content with your own -->
```

### `--pages-per-section` Behavior

```bash
bengal scaffold --sections "blog" --with-content --pages-per-section 5
```

Creates:
- `blog/_index.md`
- `blog/post-1.md`
- `blog/post-2.md`
- `blog/post-3.md`
- `blog/post-4.md`
- `blog/post-5.md`

Each with unique:
- Incrementing dates (today, yesterday, 2 days ago, etc.)
- Different titles
- Varied sample content

## Error Handling

### Existing Content

```bash
$ bengal init --sections "blog"
Error: content/blog/ already exists
Use --force to overwrite, or choose a different section name
```

### Invalid Section Names

```bash
$ bengal init --sections "blog,my page,projects"
Warning: "my page" contains spaces, converting to "my-page"
Creating sections: blog, my-page, projects
Continue? (y/n)
```

### Missing Schema File

```bash
$ bengal init --from structure.yaml
Error: structure.yaml not found
```

## Validation

### Pre-flight Checks

Before generating:
1. Verify we're in a Bengal project (has `bengal.toml`)
2. Check `content/` directory exists
3. Warn if sections already exist
4. Validate schema file syntax (if provided)

### Post-generation Validation

After generating:
1. Verify all files were created
2. Check frontmatter syntax
3. Ensure no file collisions
4. Report summary

## Output Messages

### Success

```bash
$ bengal init --sections "blog,projects" --with-content

🏗️  Initializing site structure...

✓ Created content/blog/_index.md
✓ Created content/blog/welcome-post.md
✓ Created content/blog/second-post.md
✓ Created content/blog/third-post.md
✓ Created content/projects/_index.md
✓ Created content/projects/project-alpha.md
✓ Created content/projects/project-beta.md
✓ Created content/projects/project-gamma.md

✨ Site initialized successfully!

Created:
  - 2 sections
  - 8 pages
  - 0 assets

Next steps:
  1. Review and customize generated content
  2. Run 'bengal serve' to preview your site
  3. Edit files in content/ to add your content
```

### Dry Run

```bash
$ bengal init --sections "blog,projects" --with-content --dry-run

📋 Dry run - no files will be created

Would create:
  content/blog/
    _index.md          (234 bytes)
    welcome-post.md    (456 bytes)
    second-post.md     (443 bytes)
    third-post.md      (438 bytes)
  content/projects/
    _index.md          (189 bytes)
    project-alpha.md   (512 bytes)
    project-beta.md    (498 bytes)
    project-gamma.md   (521 bytes)

Total: 8 files, 3.2 KB

Run without --dry-run to create these files
```

## Integration with `bengal new`

### Recommended: Wizard Prompt (Default)

By default, `bengal new` prompts for initialization:

```bash
$ bengal new my-site

✨ Created new Bengal site: my-site

Initialize site structure? (Y/n):
```

This ensures first-time success and guides new users.

### Alternative: Command Line Flags

For automated scripts or experienced users:

```bash
# Skip prompt entirely
bengal new my-site --no-init

# Combine with init flags
bengal new my-site --init blog,projects,about

# Use a preset
bengal new my-site --init-preset docs
```

### Alternative: Separate Step

Users can always run `bengal init` later:

```bash
bengal new my-site
cd my-site
bengal init --sections "blog,projects"
```

## Implementation Phases

### Phase 1: Core (MVP)
- [ ] `bengal init --sections "x,y,z"`
- [ ] Basic section and page generation
- [ ] Simple templates for `_index.md` and pages
- [ ] `--dry-run` support
- [ ] `--force` support

### Phase 2: Wizard Integration
- [ ] Wizard prompt in `bengal new`
- [ ] Preset selection UI
- [ ] Preview before generation
- [ ] `--no-init` flag for `bengal new`

### Phase 3: Content
- [ ] `--with-content` flag
- [ ] Sample content templates
- [ ] `--pages-per-section` option
- [ ] Smart title/slug generation

### Phase 4: Presets
- [ ] `--preset docs`
- [ ] `--preset blog`
- [ ] `--preset portfolio`
- [ ] `--preset business`

### Phase 5: Schema
- [ ] `--from structure.yaml` support
- [ ] YAML schema validation
- [ ] Custom frontmatter in schema
- [ ] Template inheritance in schema

## Testing Strategy

### Unit Tests
- Schema parsing and validation
- Template rendering
- Path generation and sanitization
- Frontmatter generation

### Integration Tests
- End-to-end scaffold generation
- File creation verification
- Content correctness
- Dry run accuracy

### Acceptance Tests
- User workflow scenarios
- Error handling
- Output formatting

## Open Questions

1. ~~**Naming**: Should it be `scaffold`, `init`, `generate`, or `setup`?~~
   - ✅ **RESOLVED**: Using `init` (more intuitive, matches industry standards)

2. ~~**Wizard Integration**: Should initialization be prompted during `bengal new`?~~
   - ✅ **RESOLVED**: Yes, wizard prompt is the recommended default experience

3. **Assets**: Should we also generate assets (images, CSS, JS)?
   - Phase 1: No
   - Future: Yes, via `--with-assets` flag

4. **Menu Configuration**: Should init auto-update navigation menus?
   - Phase 1: No (manual)
   - Future: Yes, optional via `--update-menus`

5. **Git Integration**: Should we `git add` generated files?
   - No - leave git operations to user

6. **Undo**: Should we support `bengal init --undo`?
   - Future consideration
   - For now, users can use git reset

## Examples

### Example 1: First Time User (Wizard)

```bash
$ bengal new my-blog

✨ Created new Bengal site: my-blog

Initialize site structure? (Y/n): y

> What kind of site are you building?
  1. 📝 Blog
  ...

Selection [1]: 1

> Generate sample content? (Y/n): y
> How many sample pages per section? [3]: 10

✨ Created blog with 10 sample posts!
```

### Example 2: Quick Command Line

```bash
$ cd my-site
$ bengal init --sections "blog" --with-content --pages-per-section 10

# Creates a blog with 10 sample posts
```

### Example 3: Documentation Site

```bash
$ cd docs
$ bengal init --preset docs

# Creates: getting-started, guides, reference, community sections
```

### Example 4: Custom Portfolio

```bash
$ cd portfolio
$ cat > structure.yaml << EOF
sections:
  - name: about
    pages: [bio, resume, skills]
  - name: projects
    pages: [web-apps, mobile-apps, design]
  - name: blog
  - name: contact
EOF

$ bengal init --from structure.yaml --with-content
```

### Example 5: Programmatic/CI

```bash
# Skip wizard in automation
$ bengal new my-site --no-init
$ cd my-site
$ bengal init --preset docs --with-content
$ bengal build
```

## Related Features

- **Content Adapters**: Build-time dynamic content generation
- **Site Migration**: Import from other SSGs
- **Theme Templates**: Theme-specific scaffolding
- **Component Generator**: Generate custom components

## References

- Hugo's archetypes: https://gohugo.io/content-management/archetypes/
- Jekyll's scaffolding: `jekyll new`
- Docusaurus init: `npx create-docusaurus`
- Yeoman generators: https://yeoman.io/

## Success Metrics

- Time from `bengal new` to working site < 60 seconds
- 95% of new users complete wizard successfully on first try
- 80% of users initialize structure during site creation
- Positive feedback on generated content quality
- Reduced "how do I structure my site?" support questions
- Lower churn rate for first-time users (measure via analytics)
