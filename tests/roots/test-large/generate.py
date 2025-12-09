#!/usr/bin/env python3
"""
Generate large test site content for performance testing.

Creates 100+ pages organized into sections for testing:
- Parallel rendering performance
- Large site discovery
- Memory usage
- Incremental build performance

Usage:
    python tests/roots/test-large/generate.py

Or from the test suite:
    from tests.roots.test_large.generate import generate_large_site
    generate_large_site(target_dir)
"""

from __future__ import annotations

import random
from pathlib import Path

# Page template with realistic content
PAGE_TEMPLATE = '''---
title: "{title}"
description: "{description}"
date: "2025-{month:02d}-{day:02d}"
tags:
{tags}
weight: {weight}
---

# {title}

{content}

## Section

{paragraph}

### Subsection

{list_content}

## Code Example

```python
def example_{function_name}(value: int) -> str:
    """Example function for page {page_num}."""
    return f"Result: {{value * 2}}"
```

## Links

- [[{link1}]]
- [[{link2}]]
'''

SECTIONS = [
    ("docs", "Documentation"),
    ("guides", "Guides"),
    ("tutorials", "Tutorials"),
    ("reference", "Reference"),
    ("api", "API"),
]

TAGS = [
    "python",
    "web",
    "api",
    "tutorial",
    "reference",
    "beginner",
    "advanced",
    "performance",
    "testing",
    "configuration",
    "deployment",
    "security",
    "database",
]

LOREM_PARAGRAPHS = [
    "This page demonstrates the capabilities of the Bengal static site generator. "
    "It includes various content types and formatting options commonly used in documentation.",
    "The content structure follows best practices for technical documentation, "
    "ensuring consistent formatting across all generated pages.",
    "Each page includes metadata, code examples, and cross-references to other pages "
    "to provide a realistic testing environment.",
    "Performance testing requires realistic content distribution across multiple sections "
    "and varying page sizes to accurately measure build times.",
    "The generated content includes typical elements found in documentation sites: "
    "headings, lists, code blocks, and internal links.",
]

LIST_TEMPLATES = [
    "- First item with description\n- Second item with more details\n- Third item for completeness",
    "1. Step one: Initialize\n2. Step two: Configure\n3. Step three: Deploy",
    "- **Important**: Key information\n- **Note**: Additional context\n- **Warning**: Potential issues",
]


def generate_page(section: str, page_num: int, total_pages: int) -> tuple[str, str]:
    """Generate a single page with realistic content."""
    title = f"{section.title()} Page {page_num}"
    description = f"Generated page {page_num} in {section} section for testing"

    # Random date in 2025
    month = random.randint(1, 12)
    day = random.randint(1, 28)

    # Random tags (2-4)
    num_tags = random.randint(2, 4)
    page_tags = random.sample(TAGS, num_tags)
    tags_yaml = "\n".join(f'  - "{tag}"' for tag in page_tags)

    # Random links to other pages
    other_pages = [i for i in range(1, total_pages + 1) if i != page_num]
    link1_num, link2_num = random.sample(other_pages[:20], 2)  # Link to early pages
    link1 = f"{section}/page-{link1_num}"
    link2 = f"{SECTIONS[random.randint(0, len(SECTIONS) - 1)][0]}/page-{link2_num}"

    content = PAGE_TEMPLATE.format(
        title=title,
        description=description,
        month=month,
        day=day,
        tags=tags_yaml,
        weight=page_num,
        content=random.choice(LOREM_PARAGRAPHS),
        paragraph=random.choice(LOREM_PARAGRAPHS),
        list_content=random.choice(LIST_TEMPLATES),
        function_name=f"{section}_{page_num}",
        page_num=page_num,
        link1=link1,
        link2=link2,
    )

    filename = f"page-{page_num}.md"
    return filename, content


def generate_section_index(section: str, section_title: str) -> str:
    """Generate section index page."""
    return f'''---
title: "{section_title}"
description: "{section_title} section for performance testing"
weight: {SECTIONS.index((section, section_title)) * 10 + 10}
---

# {section_title}

This section contains generated pages for performance testing.

::{{child-cards}}
:::
'''


def generate_large_site(target_dir: Path, pages_per_section: int = 20) -> None:
    """
    Generate a large test site with 100+ pages.

    Args:
        target_dir: Directory to generate content in (should be test-large root)
        pages_per_section: Number of pages per section (default: 20 = 100 total)
    """
    content_dir = target_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    total_pages = len(SECTIONS) * pages_per_section
    page_count = 0

    for section, section_title in SECTIONS:
        section_dir = content_dir / section
        section_dir.mkdir(exist_ok=True)

        # Write section index
        index_content = generate_section_index(section, section_title)
        (section_dir / "_index.md").write_text(index_content)

        # Generate pages for this section
        for i in range(1, pages_per_section + 1):
            page_count += 1
            filename, content = generate_page(section, i, total_pages)
            (section_dir / filename).write_text(content)

    print(f"Generated {page_count} pages in {len(SECTIONS)} sections")
    print(f"Total site size: ~{page_count * 2}KB of markdown")


def main() -> None:
    """Generate large test site content."""
    # Find test-large directory
    script_dir = Path(__file__).parent
    generate_large_site(script_dir, pages_per_section=20)


if __name__ == "__main__":
    main()
