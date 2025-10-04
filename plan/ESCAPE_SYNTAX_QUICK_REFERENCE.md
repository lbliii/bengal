# Escape Syntax Quick Reference

## The Problem
```
Current: {{/* page.title */}}  ❌ BROKEN (conflicts with markdown)
Output:  {{/<em> page.title </em>/}}
```

## Solutions at a Glance

### 🏆 RECOMMENDED: `{{% %}}`
```markdown
Use {{% page.title %}} to display the page title.
Format dates: {{% page.date | format_date('%Y-%m-%d') %}}
```
**Output:** `{{ page.title }}` and `{{ page.date | format_date('%Y-%m-%d') }}`

**Why:** No Markdown conflicts, clean syntax, easy to remember.

---

### ✅ ALREADY WORKS: `preprocess: false`
```markdown
---
title: "Template Reference"
preprocess: false
---

{{ page.title }}
{% for post in posts %}
  {{ post.title }}
{% endfor %}
```
**All syntax stays literal!**

**Why:** Perfect for full documentation pages.

---

### ✅ ALREADY WORKS: Backticks
```markdown
Use `{{ page.title }}` to display the page title.
```
**Output:** Use <code>{{ page.title }}</code> to display the page title.

**Why:** Natural for code examples, already works.

---

## Use Case Matrix

| Scenario | Best Approach | Example |
|----------|---------------|---------|
| **Inline example in prose** | `{{% %}}` | Use {{% page.title %}} to display... |
| **Full doc page** | `preprocess: false` | Entire file of examples |
| **Function signature** | Backticks | `` `{{ var }}` `` |
| **Code block** | Nothing! | Already literal in ``` blocks |

---

## Quick Decision Tree

```
Do you need to mix real and escaped variables in ONE page?
├─ YES → Use {{% %}} for escaped examples
└─ NO  → Is the ENTIRE page documentation?
    ├─ YES → Use preprocess: false
    └─ NO  → Are you showing CODE?
        ├─ YES → Use backticks
        └─ NO  → Use {{% %}}
```

---

## Migration Path

### Step 1: Add {{% %}} support (1 line change)
```python
ESCAPE_PATTERN = re.compile(r'\{\{%\s*(.+?)\s*%\}\}')
```

### Step 2: Update showcase examples
```bash
# Find and replace
find examples/showcase -name "*.md" -exec sed -i '' 's/{{\/\*/{{%/g; s/\*\/}}/\%}}/g' {} \;
```

### Step 3: Update tests
```python
# Old
doc_page.write_text("Use {{/* page.title */}} to display...")

# New
doc_page.write_text("Use {{% page.title %}} to display...")
```

---

## Implementation Effort

| Task | Time | Risk |
|------|------|------|
| Change regex | 2 min | Low |
| Update tests | 10 min | Low |
| Update showcase docs | 15 min | Low |
| Update main docs | 20 min | Low |
| Add migration script | 30 min | Medium |
| **TOTAL** | **~1 hour** | **Low** |

---

## Recommendation

**Implement `{{% %}}` syntax now:**
1. Simple, clean, no conflicts
2. Easy migration (~1 hour)
3. Future-proof
4. Familiar to Hugo users

Keep existing options documented:
- `preprocess: false` for full doc pages
- Backticks for code examples
- Code blocks are naturally literal

**Result:** Three complementary approaches for different use cases!
