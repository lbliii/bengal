# CSS Scoping - Quick Reference Card

**Keep this handy when writing CSS!**

---

## The Golden Rule

> **Every selector must be scoped. Never write bare element selectors in components.**

---

## Quick Decision Tree

```
Need to style content?
│
├─ Is it markdown/user HTML?
│  ├─ YES → Use .has-prose-content utility
│  └─ NO  → Continue...
│
├─ Is it API documentation specific?
│  ├─ YES → Use .prose.api-content
│  └─ NO  → Continue...
│
├─ Is it component-specific styling?
│  ├─ YES → Scope to .component-name
│  └─ NO  → Use .prose (if typography)
```

---

## Common Patterns

### ✅ Good Examples

```css
/* Component scoping */
.dropdown-content ul { list-style: disc; }

/* Content type scoping */
.prose.api-content p + ul { border: 1px solid var(--color-border); }

/* Utility class */
.has-prose-content ul { list-style: disc; }

/* Direct child */
.card-body > ul { margin: 0; }
```

### ❌ Bad Examples

```css
/* Too broad - affects everything */
.prose ul { border: 1px solid red; }

/* Bare element selector in component file */
ul { list-style: none; }

/* Deep nesting */
.prose .card .dropdown ul li a { color: blue; }
```

---

## Selector Hierarchy

**From lowest to highest specificity:**

1. **Base:** `ul` (in reset.css only)
2. **Prose:** `.prose ul` (typography.css)
3. **Content Type:** `.prose.api-content ul` (api-docs.css)
4. **Component:** `.dropdown-content ul` (dropdown.css)
5. **State:** `.dropdown-content.is-open ul` (dropdown.css)

---

## When to Use What

| Situation | Use This | Example |
|-----------|----------|---------|
| User content container | `.has-prose-content` | `<div class="card-body has-prose-content">` |
| API docs specific | `.prose.api-content` | `.prose.api-content p + ul` |
| Component styling | `.component-name` | `.dropdown-content ul` |
| UI lists (nav, etc.) | Explicit reset | `.nav-list { list-style: none; }` |
| Typography only | `.prose` | `.prose h2` (in typography.css) |

---

## File Organization

```
base/
  reset.css          → Bare elements only (ul, ol, p)
  typography.css     → .prose elements only
  prose-content.css  → .has-prose-content utility ⭐

components/
  dropdown.css       → .dropdown* scoping
  api-docs.css       → .prose.api-content scoping
  cards.css          → .card* scoping
```

---

## Common Mistakes

### ❌ Mistake #1: Broad .prose selector in component
```css
/* In api-docs.css */
.prose ul { border: 1px solid blue; }  /* Affects ALL prose! */
```

**Fix:**
```css
.prose.api-content ul { border: 1px solid blue; }
```

---

### ❌ Mistake #2: Forgetting about nested components
```css
.card-body ul { list-style: square; }
/* But what if card contains a dropdown? */
```

**Fix:**
```css
.card-body > ul { list-style: square; }  /* Direct child */
/* OR */
.card-body.has-prose-content ul { ... }  /* Utility pattern */
```

---

### ❌ Mistake #3: Using !important
```css
.prose ul { list-style: disc !important; }
```

**Fix:** Use more specific selector instead

---

## Checklist Before Committing CSS

- [ ] All selectors are scoped to a class
- [ ] No bare element selectors (except in reset.css)
- [ ] Used `.has-prose-content` for generic containers
- [ ] Content-type specific styles use `.prose.api-content` etc.
- [ ] Tested with nested components
- [ ] No `!important` (unless documented why)
- [ ] Works in both light and dark mode

---

## Template Updates

**Add utility class to content containers:**

```html
<!-- Before -->
<div class="dropdown-content">
  {{ content }}
</div>

<!-- After -->
<div class="dropdown-content has-prose-content">
  {{ content }}
</div>
```

---

## Content Type Classes

**Add to article/page templates:**

```jinja
<article class="prose {{ page.content_type|default('article') }}">
  {{ content }}
</article>
```

**Available types:**
- `api-content` - Auto-generated API docs
- `reference` - Reference documentation
- `tutorial` - Step-by-step guides
- `blog-post` - Blog articles
- `guide` - How-to guides

---

## Testing

**Always test:**
1. Regular markdown pages
2. API documentation pages
3. Pages with nested components
4. Dark mode
5. Mobile views

---

## Need Help?

1. Read [CSS_SCOPING_RULES.md](./CSS_SCOPING_RULES.md) for full details
2. Check [CSS_ARCHITECTURE_REVIEW.md](../plan/completed/CSS_ARCHITECTURE_REVIEW.md) for rationale
3. See [CSS_SCOPING_IMPLEMENTATION_PLAN.md](../plan/CSS_SCOPING_IMPLEMENTATION_PLAN.md) for migration guide

---

## Emergency Override

**If you MUST break the rules:**

```css
/* TECH DEBT: Temporary override for [ISSUE-123]
 * TODO: Refactor when [CONDITION]
 * @see [LINK TO ISSUE]
 */
.prose ul {
  border: 1px solid red !important;
}
```

**Document:**
- Why it's needed
- When it will be fixed
- Link to issue/ticket

---

**Remember:** When in doubt, scope it! 🎯
