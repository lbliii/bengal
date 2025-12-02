# RFC: 404 Page Redesign

**Status**: ✅ Implemented  
**Author**: AI Assistant  
**Created**: 2025-12-02

---

## Summary

Redesign the 404 page to provide dynamic, site-aware navigation suggestions instead of hardcoded links, remove redundant search UI, and create a cleaner user experience.

---

## Problem Statement

The current 404 page has several issues:

1. **Hardcoded links** (`/blog/`, `/tags/`, `/search/`) assume specific site structure
2. **Redundant search button** - Global search (⌘K) is always available in header
3. **Generic suggestions** - "Visit the homepage" and "Use the navigation menu" are unhelpful
4. **Repetitive content** - Search mentioned 3 times (button + 2 list items)

---

## Goals

- [ ] Dynamic suggestions based on actual site navigation
- [ ] Remove redundant search button
- [ ] Add keyboard shortcut hint for search
- [ ] Cleaner, more helpful UX

## Non-Goals

- Adding sidebars (inappropriate for error pages)
- Complex interactivity
- Site-wide search from the 404 page itself

---

## Design

### Before vs After

**Before (hardcoded):**
```
- Visit the homepage
- Browse all posts       ← assumes /blog/ exists
- Explore by tags        ← assumes /tags/ exists  
- Search the site        ← redundant, 3x mentioned
- Use the navigation menu above
```

**After (dynamic):**
```
Quick navigation:
- [Home icon] Homepage
- [Dynamic] First 3-4 nav items from site menu
- [Keyboard] Press ⌘K to search
```

### Template Changes

```jinja
{# Get actual navigation items #}
{% set main_menu = get_menu_lang('main', current_lang()) %}
{% set auto_nav = [] %}
{% if main_menu | length == 0 %}
{% set auto_nav = get_auto_nav() %}
{% endif %}
{% set nav_items = main_menu if main_menu else auto_nav %}

{# Dynamic suggestions based on real site structure #}
<div class="empty-state__suggestions">
  <h2>Quick Navigation</h2>
  <ul>
    <li>
      <a href="{{ '/' | absolute_url }}">
        <svg><!-- home icon --></svg>
        Homepage
      </a>
    </li>
    {% for item in nav_items[:4] %}
    <li>
      <a href="{{ item.url | absolute_url }}">{{ item.name }}</a>
    </li>
    {% endfor %}
  </ul>
  
  {# Search hint instead of button #}
  <p class="empty-state__search-hint">
    <kbd>⌘</kbd><kbd>K</kbd> to search
  </p>
</div>
```

### Visual Changes

1. **Remove**: Secondary "Search" button from actions
2. **Keep**: Single "Go Home" primary button
3. **Add**: Keyboard shortcut hint styled as subtle kbd elements
4. **Dynamic**: Pull actual nav items instead of assumptions

---

## CSS Additions

```css
.empty-state__search-hint {
  margin-top: var(--space-6);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.empty-state__search-hint kbd {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
```

---

## Implementation Plan

1. Update `404.html` template with dynamic nav
2. Add search hint styling to `empty-state.css`
3. Test with sites that have/don't have configured menus

---

## Alternatives Considered

### A. Add sidebars like doc pages
**Rejected**: 404 pages should be simple and focused. Sidebars add cognitive load when the user is already disoriented.

### B. Keep search button, just fix links
**Rejected**: Redundant UI. Global search is always available.

### C. Add inline search box
**Rejected**: Duplicates functionality. Better to hint at existing feature.

---

## Open Questions

1. Should we show a random "featured" page as a suggestion?
2. Add a "Report broken link" option?

