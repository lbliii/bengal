---
title: Set Up Content Workflow
description: Set up an efficient workflow for creating, reviewing, and publishing content
weight: 20
draft: false
lang: en
tags: [content, workflow, publishing, drafts, git]
keywords: [content workflow, drafts, publishing, git, version control]
category: guide
---

# Set Up Content Workflow

Establish an efficient workflow for creating, reviewing, and publishing content. Manage drafts, use version control effectively, and automate your publishing process.

## When to Use This Guide

```{checklist}
- You're creating content regularly (blog, documentation, etc.)
- You need to manage drafts and work-in-progress content
- You want to set up a content review process
- You're working with a team on content
- You need scheduled or automated publishing
```

## Prerequisites

- [Bengal installed](/docs/getting-started/installation/)
- Basic knowledge of Git
- A Bengal site set up (see [Writer Quickstart](/docs/getting-started/writer-quickstart/))

## Step 1: Understand Draft Management

### Draft Frontmatter

Bengal excludes pages with `draft: true` from builds by default:

```yaml
---
title: Work in Progress
draft: true  # This page won't appear in builds
---
```

### Building with Drafts

To include drafts during development:

```bash
# Build with drafts included
bengal site build --build-drafts

# Dev server always shows drafts
bengal site serve  # Drafts visible automatically
```

### Draft Workflow Pattern

1. **Create draft:**
   ```bash
   bengal new page my-post --section blog
   ```

2. **Edit frontmatter:**
   ```yaml
   ---
   title: My Post
   draft: true  # Mark as draft
   date: 2025-10-26  # Set future date for scheduling
   ---
   ```

3. **Preview locally:**
   ```bash
   bengal site serve
   # Draft is visible at http://localhost:5173/blog/my-post/
   ```

4. **Publish:**
   ```yaml
   ---
   title: My Post
   draft: false  # Change to false to publish
   date: 2025-10-26
   ---
   ```

## Step 2: Organize Your Content Structure

### Recommended Structure

```
content/
├── blog/
│   ├── _index.md          # Blog section page
│   ├── 2025/
│   │   ├── 10/
│   │   │   ├── post-1.md  # Published posts
│   │   │   └── post-2.md
│   │   └── drafts/
│   │       └── wip-post.md # Drafts folder
│   └── _drafts/           # Alternative: separate drafts folder
│       └── future-post.md
├── docs/
│   ├── _index.md
│   └── guides/
│       └── getting-started.md
└── pages/
    ├── about.md
    └── contact.md
```

### Content Organization Strategies

**Option 1: Date-based organization**
```bash
content/blog/2025/10/post.md
```
- Pros: Easy to find posts by date
- Cons: Requires moving files when publishing

**Option 2: Drafts folder**
```bash
content/blog/_drafts/post.md  # Move to content/blog/ when ready
```
- Pros: Clear separation of drafts
- Cons: Requires file movement

**Option 3: Draft flag only**
```bash
content/blog/post.md  # Use draft: true/false
```
- Pros: Simple, no file movement
- Cons: Drafts mixed with published content

**Recommendation:** Use Option 3 (draft flag) for simplicity, or Option 2 if you prefer visual separation.

## Step 3: Set Up Git Workflow

### Branch Strategy

**For solo authors:**
```bash
main          # Published content only
├── draft-*   # Feature branches for drafts
```

**For teams:**
```bash
main          # Production content
├── develop   # Staging/preview
├── content/* # Content branches (content/blog-post-title)
```

### Git Workflow Example

1. **Create content branch:**
   ```bash
   git checkout -b content/new-blog-post
   ```

2. **Create and edit content:**
   ```bash
   bengal new page new-post --section blog
   # Edit content/blog/new-post.md
   ```

3. **Commit draft:**
   ```bash
   git add content/blog/new-post.md
   git commit -m "content: add draft blog post 'New Post'"
   ```

4. **Preview and review:**
   ```bash
   bengal site serve
   # Share preview URL or create PR for review
   ```

5. **Publish:**
   ```bash
   # Edit frontmatter: draft: false
   git add content/blog/new-post.md
   git commit -m "content: publish 'New Post'"
   git push origin content/new-blog-post
   ```

6. **Merge to main:**
   ```bash
   git checkout main
   git merge content/new-blog-post
   git push origin main
   ```

## Step 4: Content Review Process

### Using Pull Requests

For team collaboration:

1. **Create PR with draft:**
   ```bash
   git checkout -b content/review-post
   # Create/edit content
   git push origin content/review-post
   # Create PR on GitHub/GitLab
   ```

2. **Review checklist:**
   - [ ] Frontmatter complete (title, date, tags)
   - [ ] Content proofread
   - [ ] Links verified
   - [ ] Images optimized
   - [ ] SEO metadata present

3. **Approve and merge:**
   - Reviewer approves PR
   - Merge to main triggers deployment

### Preview URLs

For external reviewers:

1. **Deploy preview branch:**
   ```bash
   # Using Netlify/Vercel preview deployments
   # PR automatically creates preview URL
   ```

2. **Share preview:**
   - Share Netlify/Vercel preview URL
   - Or use `bengal site serve --host 0.0.0.0` for local network access

## Step 5: Content Templates

### Create Content Templates

Create reusable templates for consistent frontmatter:

**`templates/blog-post.md`:**
```yaml
---
title: {{title}}
date: {{date}}
tags: []
category: blog
draft: true
description: ""
---
```

### Use Templates

```bash
# Copy template
cp templates/blog-post.md content/blog/new-post.md

# Edit placeholders
# Or use bengal new page with --template flag (if supported)
```

## Step 6: Automated Publishing

### Scheduled Publishing with CI/CD

Use GitHub Actions to check for scheduled posts:

```yaml
# .github/workflows/publish.yml
name: Publish Scheduled Posts

on:
  schedule:
    - cron: '0 * * * *'  # Check every hour
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install Bengal
        run: pip install bengal

      - name: Check for scheduled posts
        run: |
          python scripts/check-scheduled-posts.py

      - name: Commit and push changes
        if: github.event_name == 'schedule'
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add content/
          git commit -m "content: publish scheduled posts" || exit 0
          git push
```

**`scripts/check-scheduled-posts.py`:**
```python
#!/usr/bin/env python3
"""Check for scheduled posts and publish them."""

from pathlib import Path
from datetime import datetime
import frontmatter

content_dir = Path("content")
now = datetime.now()

for md_file in content_dir.rglob("*.md"):
    post = frontmatter.load(md_file)

    # Check if draft with past date
    if post.get("draft") and post.get("date"):
        post_date = post["date"]
        if isinstance(post_date, str):
            post_date = datetime.fromisoformat(post_date.replace("Z", "+00:00"))

        if post_date <= now:
            # Publish the post
            post["draft"] = False
            with open(md_file, "w") as f:
                frontmatter.dump(post, f)
            print(f"Published: {md_file}")
```

## Step 7: Content Validation

### Pre-commit Hooks

Validate content before committing:

**`.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: local
    hooks:
      - id: validate-frontmatter
        name: Validate Frontmatter
        entry: python scripts/validate-frontmatter.py
        language: system
        files: \.md$
```

**`scripts/validate-frontmatter.py`:**
```python
#!/usr/bin/env python3
"""Validate frontmatter in markdown files."""

import sys
from pathlib import Path
import frontmatter

errors = []

for md_file in Path("content").rglob("*.md"):
    try:
        post = frontmatter.load(md_file)

        # Check required fields
        if not post.get("title"):
            errors.append(f"{md_file}: Missing 'title' field")

        # Validate date format
        if post.get("date"):
            date = post["date"]
            if isinstance(date, str):
                try:
                    datetime.fromisoformat(date.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"{md_file}: Invalid date format")

    except Exception as e:
        errors.append(f"{md_file}: {e}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
```

## Step 8: Content Statistics

### Track Content Metrics

**`scripts/content-stats.py`:**
```python
#!/usr/bin/env python3
"""Generate content statistics."""

from pathlib import Path
import frontmatter
from collections import Counter

content_dir = Path("content")
stats = {
    "total_pages": 0,
    "drafts": 0,
    "published": 0,
    "by_section": Counter(),
    "by_tag": Counter(),
}

for md_file in content_dir.rglob("*.md"):
    post = frontmatter.load(md_file)
    stats["total_pages"] += 1

    if post.get("draft"):
        stats["drafts"] += 1
    else:
        stats["published"] += 1

    # Section stats
    section = md_file.parent.name
    stats["by_section"][section] += 1

    # Tag stats
    for tag in post.get("tags", []):
        stats["by_tag"][tag] += 1

print(f"Total pages: {stats['total_pages']}")
print(f"Published: {stats['published']}")
print(f"Drafts: {stats['drafts']}")
print(f"\nBy section: {dict(stats['by_section'])}")
print(f"\nTop tags: {stats['by_tag'].most_common(10)}")
```

## Troubleshooting

### Common Issues

**Drafts appearing in production:**
- Check `draft: false` in frontmatter
- Verify build command doesn't include `--build-drafts`
- Check CI/CD configuration

**Content not updating:**
- Clear cache: `bengal site clean --cache`
- Rebuild: `bengal site build`
- Check file is in `content/` directory

**Git conflicts:**
- Use `git merge` or rebase carefully
- Consider using `content/` directory as merge strategy
- Use `.gitattributes` to set merge strategy

**Preview not working:**
- Ensure dev server is running: `bengal site serve`
- Check port isn't blocked: `bengal site serve --port 8080`
- Verify content files are saved

## Next Steps

- **[Migrating Content](/docs/guides/migrating-content/)** - Migrate from another SSG
- **[Customizing Themes](/docs/guides/customizing-themes/)** - Customize your site's appearance
- **[CI/CD Setup](/docs/guides/ci-cd-setup/)** - Automate your publishing workflow
