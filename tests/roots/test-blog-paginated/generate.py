#!/usr/bin/env python3
"""
Generate blog test content with 25 posts for pagination testing.

Creates a blog structure with:
- 25 posts with dates spanning 2025
- Various tags and categories
- About page (static)
- Blog index

Usage:
    python tests/roots/test-blog-paginated/generate.py

Or from the test suite:
    from tests.roots.test_blog_paginated.generate import generate_blog
    generate_blog(target_dir)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

POST_TEMPLATE = """---
title: "{title}"
date: {date}
tags:
{tags}
categories:
  - {category}
author: "Test Author"
description: "Post #{num} for pagination testing"
---

# {title}

This is post number {num} in the test blog.

## Introduction

{content}

## Details

This post was generated for testing blog pagination, RSS feeds, and sorting.

### Key Points

- Point 1 for post {num}
- Point 2 for post {num}
- Point 3 for post {num}

## Conclusion

End of post {num}.
"""

CONTENT_SAMPLES = [
    "This post explores testing patterns for static site generators.",
    "An in-depth look at pagination strategies for large blogs.",
    "How to optimize RSS feed generation for performance.",
    "Understanding date-based sorting in content management.",
    "Best practices for organizing blog content in Bengal.",
]

TAGS = [
    ["python", "testing"],
    ["web", "development"],
    ["tutorial", "beginner"],
    ["advanced", "performance"],
    ["api", "reference"],
    ["python", "web"],
    ["testing", "tutorial"],
    ["development", "beginner"],
]

CATEGORIES = ["Technology", "Development", "Tutorial", "News", "Review"]


def generate_post(num: int, date: datetime) -> tuple[str, str]:
    """Generate a single blog post."""
    title = f"Blog Post {num:02d}: Test Pagination"

    # Pick tags and category based on post number
    tags = TAGS[num % len(TAGS)]
    tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
    category = CATEGORIES[num % len(CATEGORIES)]

    content = POST_TEMPLATE.format(
        title=title,
        date=date.strftime("%Y-%m-%d"),
        tags=tags_yaml,
        category=category,
        num=num,
        content=CONTENT_SAMPLES[num % len(CONTENT_SAMPLES)],
    )

    filename = f"post-{num:02d}.md"
    return filename, content


def generate_blog(target_dir: Path, num_posts: int = 25) -> None:
    """
    Generate a blog test site with paginated posts.

    Args:
        target_dir: Directory to generate content in
        num_posts: Number of posts to generate (default: 25)

    """
    content_dir = target_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Create blog index
    blog_index = content_dir / "_index.md"
    blog_index.write_text("""---
title: "Test Blog"
description: "Blog for testing pagination"
type: blog
---

# Test Blog

Welcome to the test blog for pagination testing.
""")

    # Create posts directory
    posts_dir = content_dir / "posts"
    posts_dir.mkdir(exist_ok=True)

    # Create posts section index
    posts_index = posts_dir / "_index.md"
    posts_index.write_text("""---
title: "Posts"
description: "All blog posts"
type: blog
layout: list
---

# Blog Posts

All posts in the test blog.
""")

    # Generate posts with dates spanning 2025
    # Posts are numbered 1-25, with post-25 being most recent
    base_date = datetime(2025, 1, 1)

    for i in range(1, num_posts + 1):
        # Space posts ~2 weeks apart
        post_date = base_date + timedelta(days=(i - 1) * 14)
        filename, content = generate_post(i, post_date)
        (posts_dir / filename).write_text(content)

    # Create static about page
    about = content_dir / "about.md"
    about.write_text("""---
title: "About"
description: "About this blog"
type: page
---

# About This Blog

This is a test blog for pagination testing.

## Purpose

- Test pagination with 25 posts
- Test RSS feed generation
- Test date-based sorting
- Test tag/category taxonomies
""")

    print(f"Generated {num_posts} posts + about page")
    print(
        f"Posts span from {base_date.strftime('%Y-%m-%d')} to {(base_date + timedelta(days=(num_posts - 1) * 14)).strftime('%Y-%m-%d')}"
    )


def main() -> None:
    """Generate blog test content."""
    script_dir = Path(__file__).parent
    generate_blog(script_dir, num_posts=25)


if __name__ == "__main__":
    main()
