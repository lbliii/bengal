---
title: Content Strategy Guides Plan
status: active
owner: llane
started: 2025-11-25
target_release: 0.1.5
---

# Content Strategy Guides

Plan to add advanced "Jobs to be Done" guides for content creators and strategists.

## 1. Content Reuse: "Write Once, Publish Everywhere"

**Goal**: Teach how to manage shared content (warnings, pricing, definitions) centrally.

**Techniques**:
- **Data Files**: Storing text in `site/data/` (e.g., `glossary.yaml`, `alerts.yaml`).
- **Templates**: Injecting data into layouts.
- **Custom Directive**: Implementing a simple `{include}` directive for Markdown reuse (since native support is missing).

**Structure**:
- Why reuse content? (Consistency, Maintenance)
- Strategy 1: The Data File approach (Global strings)
- Strategy 2: The Layout approach (Shared components)
- Strategy 3: The Directive approach (In-content snippets) -> *Requires coding a small plugin*

## 2. Curated Tracks: "Building Composite Learning Paths"

**Goal**: Create linear "courses" or "tracks" from existing independent articles.

**Techniques**:
- **Data Files**: Defining tracks in `site/data/tracks.yaml`.
- **Layouts**: Creating a `layouts/track/single.html` that adds "Next/Prev" and progress bars.
- **Frontmatter**: associating pages with tracks.

**Structure**:
- Concept: Sets vs. Sequences
- Step 1: Define your track (YAML)
- Step 2: Create the navigation logic (Jinja)
- Step 3: The Track Layout

## 3. Advanced Filtering: "Building Tag Intersections"

**Goal**: Create dynamic pages that filter content by multiple criteria.

**Techniques**:
- **Taxonomies**: Accessing `site.taxonomies`.
- **Jinja Logic**: Set intersection/union logic.
- **URL Parameters**: (Optional) Client-side vs. Static Generation (creating `/tags/python+advanced/`).

**Structure**:
- The problem with single tags
- Logic: Set Theory in Jinja
- Implementation: The "Filter Page" Template

## Implementation Order

1.  **Curated Tracks** (High impact for documentation sites)
2.  **Content Reuse** (High utility)
3.  **Advanced Filtering** (Niche but powerful)

