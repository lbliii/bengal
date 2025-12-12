# RFC: Shareable Site Skeletons (The Component Model)

**Status**: Draft
**Author**: AI Assistant
**Created**: 2025-12-06
**Priority**: HIGH

---

## Summary

Add `bengal skeleton apply <manifest.yaml>` to hydrate a site structure from a declarative YAML file. This introduces a formal **Component Model** for pages, aligning the backend (`PageCore`) with the frontend (Themes/Templates).

**Key Concept**: Treat pages as components with **Identity** (Type), **Mode** (Variant), and **Data** (Props).

---

## The Problem

Currently, `bengal init` is imperative and limited. It creates generic files without semantic structure. Users can't:
1.  Define complex nested structures declaratively.
2.  Share site patterns (e.g., "Documentation Site", "Blog", "Landing Page") as simple files.
3.  Clearly distinguish between **Structural Logic** (Sorting/Routing) and **Visual Style** (CSS/Layouts).

---

## The Solution: The Component Model

We adopt a "Component Props" mental model (similar to Figma/React) to clarify the configuration.

| Concept | Terminology | Schema Key | Definition | Example |
| :--- | :--- | :--- | :--- | :--- |
| **Identity** | **Type** | `type` | **What is it?**<br>Determines Logic (Sorting) & Template Family. | `blog`, `doc`, `api` |
| **Mode** | **Variant** | `variant` | **How does it look?**<br>Determines Visual State (CSS/Hero). | `magazine`, `wide` |
| **Data** | **Props** | `props` | **What data does it have?**<br>Content passed to template (Frontmatter). | `author`, `banner` |

### Schema Design

```yaml
structure:
  - path: blog/
    # 1. IDENTITY (Routing & Logic)
    # - Sorts by Date (BlogStrategy)
    # - Uses templates/blog/*.html
    type: blog

    # 2. MODE (Visual Style)
    # - Sets CSS class .variant-magazine
    # - Selects partials/hero-magazine.html
    variant: magazine

    # 3. DATA (Frontmatter)
    # - Merged into page.metadata
    props:
      title: "Engineering Blog"
      description: "Deep dives into our stack."
      banner_image: "/images/team.jpg"

    # 4. CASCADE (Inheritance)
    cascade:
      type: blog          # All children are blog posts
      variant: standard   # All children use standard layout
```

---

## PageCore Refactor

To support this performance-efficiently, we promote key fields to `PageCore`.

**Current `PageCore`**:
```python
class PageCore:
    type: str | None
    # layout/hero/description are hidden in metadata dict (slow access)
```

**Proposed `PageCore`**:
```python
@dataclass
class PageCore(Cacheable):
    # --- Identity ---
    source_path: str
    type: str | None = None      # Routing/Strategy

    # --- Mode ---
    variant: str | None = None   # Visual variant (Replaces layout/hero_style)

    # --- Core Props (Promoted for Performance) ---
    title: str
    description: str | None = None  # Critical for SEO/RSS/Listings

    # ... date, tags, weight, etc.
```

### Migration / Hydration Logic
The `skeleton apply` command (Hydrator) normalizes legacy terms into this model:

*   `layout: foo` $\to$ `variant: foo`
*   `hero_style: bar` $\to$ `variant: bar`
*   `metadata: {}` $\to$ `props: {}` (Aliased)

---

## CLI Usage

```bash
# Apply a local skeleton
bengal skeleton apply my-site.yaml

# Apply from URL (Gist/GitHub)
bengal skeleton apply https://gist.github.com/.../docs-site.yaml

# Layering (Composition)
bengal skeleton apply base.yaml --layer blog.yaml --layer docs.yaml
```

---

## Implementation Plan

### Phase 1: The Core Model (Backend)
- [ ] Refactor `PageCore`: Add `variant` and `description`.
- [ ] Update `Page` and `PageProxy` delegates.
- [ ] Update `strategies.py` to confirm `type` remains the primary logic driver.

### Phase 2: The Hydrator (CLI)
- [x] Implement `bengal/cli/skeleton/schema.py` (Dataclass model).
- [x] Implement `bengal/cli/skeleton/hydrator.py` (YAML $\to$ Files).
- [x] Implement `bengal/cli/commands/skeleton.py`.
- [x] Register command in CLI (`bengal project skeleton apply`).
- [x] Convert templates to skeleton manifests (`blog`, `docs`, `portfolio`).
- [x] Update template registry to prefer skeleton manifests with Python fallback.

### Phase 3: The Theme (Frontend)
- [ ] Update `base.html` to output `data-variant="{{ page.core.variant }}"`.
- [ ] Update `page-hero.html` to switch on `variant` instead of `hero_style`.

---

## FAQ

**Q: Why not rename `type` to `template`?**
A: `type` controls more than just the template file. It controls **Data Logic** (e.g., `BlogStrategy` sorts by date, `DocStrategy` sorts by weight). Renaming it to `template` would hide this behavior.

**Q: What happens to `layout` frontmatter?**
A: It becomes an alias for `variant`. We will support it for backward compatibility in the Hydrator, but `PageCore` will store it as `variant`.

**Q: Can I override the template file directly?**
A: Yes, via `template: "custom/path.html"` in `props` (standard frontmatter override), but this is rare. The Component Model prefers `type` + `variant`.
