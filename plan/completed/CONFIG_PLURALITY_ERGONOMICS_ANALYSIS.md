# Configuration Plurality: Ergonomics Analysis
**Date:** October 4, 2025  
**Question:** Should we accept both `[menu]`/`[menus]`, `[taxonomy]`/`[taxonomies]`, etc?

## The Problem

Users naturally type what feels right:
- Some write `[[menu.main]]` (singular - one menu definition)
- Others write `[[menus.main]]` (plural - section containing menus)
- Both are linguistically correct!

**Current behavior:** Silently ignores `[menus]`, causing confusion.

## Plurality in Config: Industry Analysis

### 1. **Hugo** (Go-based SSG)
```toml
# Accepts BOTH! (very ergonomic)
[menu]
[[menu.main]]
  name = "Home"

# Also works:
[menus]
[[menus.main]]
  name = "Home"
```

**Result:** Hugo normalizes both to the same internal structure. ✅

### 2. **Gatsby** (JavaScript)
```javascript
// Uses plural arrays
module.exports = {
  plugins: [...],      // Plural
  siteMetadata: {...}  // Singular object
}
```

**Pattern:** Arrays are plural, objects are singular. ✅

### 3. **Jekyll** (Ruby)
```yaml
# Uses plural for collections
collections:
  posts:
    output: true
    
# Singular for configuration
permalink: /blog/:title/
```

**Pattern:** Collections plural, settings singular. ✅

### 4. **Next.js** (JavaScript)
```javascript
// Strictly singular, even for arrays
module.exports = {
  image: {        // Singular even though multiple images
    domains: []
  }
}
```

**Pattern:** Always singular config keys. ⚠️

### 5. **Django** (Python)
```python
# Python conventions: plural for lists
INSTALLED_APPS = [...]      # Plural
MIDDLEWARE = [...]           # Plural
ROOT_URLCONF = '...'        # Singular

# Accepts BOTH in some cases:
TEMPLATE_DIRS = [...]        # Old
TEMPLATES = [...]            # New
```

**Pattern:** Python uses plural for lists, accepts legacy names. ✅

## Linguistic Analysis

### When Plural Makes Sense

**Container of multiple items:**
```toml
[menus]           # ✅ Natural: "the menus section"
[[menus.main]]    # "one of the menus"
[[menus.footer]]  # "another menu"

[taxonomies]      # ✅ Natural: "the taxonomies section"
tags = "tags"
categories = "categories"
```

### When Singular Makes Sense

**Direct definition:**
```toml
[[menu.main]]     # ✅ Natural: "the main menu"
[[menu.footer]]   # "the footer menu"

[site]            # ✅ Natural: "site configuration"
title = "..."
```

### The Ambiguity

TOML uses `[[section.item]]` for arrays:
```toml
# Is this...
[[menu.main]]     # The main menu (singular)?
# or
[[menus.main]]    # One entry in the menus collection (plural)?
```

**Both are linguistically valid!**

## User Mental Models

### Model 1: "Section Container"
```toml
[menus]            # Plural: section contains multiple menu definitions
[[menus.main]]     # Each menu definition
[[menus.footer]]
```

**User thinking:** "I'm defining multiple menus, so the section is `[menus]`"

### Model 2: "Item Type"
```toml
[[menu.main]]      # Singular: each definition is "a menu"
[[menu.footer]]    # Another "menu"
```

**User thinking:** "Each `[[menu.X]]` is a menu item, so it's singular"

### Model 3: "Hugo Style"
```toml
[menu]             # Singular section (legacy Hugo)
[[menu.main]]      # Menu items within
```

**User thinking:** "I'm copying Hugo config syntax"

## Proposed Solution: Flexible Aliases

### Accept Both Forms
```python
# In config/loader.py
SECTION_ALIASES = {
    'menus': 'menu',
    'taxonomies': 'taxonomies',  # Keep plural
    'template': 'templates',
    'plugin': 'plugins',
}

def _normalize_config(self, config: dict) -> dict:
    """Normalize config, accepting common aliases."""
    normalized = {}
    
    for key, value in config.items():
        # Check if key has an alias
        canonical = SECTION_ALIASES.get(key, key)
        
        # Merge with canonical key if both exist
        if canonical in normalized and canonical != key:
            # Both [menu] and [menus] present - merge them
            if isinstance(value, dict):
                normalized[canonical].update(value)
            else:
                # Conflict - warn user
                print(f"⚠️  Both [{key}] and [{canonical}] defined. Using [{canonical}].")
        else:
            normalized[canonical] = value
    
    return normalized
```

### Example: Accepting Both
```toml
# User writes either:
[[menu.main]]       # ✅ Works
name = "Home"

# Or:
[[menus.main]]      # ✅ Also works (normalized to menu.main)
name = "Home"
```

**Both get normalized to internal `menu` structure.**

## Pros and Cons

### ✅ PROS: Accept Plurality

1. **Ergonomic:** Matches user intuition
2. **Forgiving:** Reduces configuration errors
3. **Migration-friendly:** Works with Hugo/Jekyll configs
4. **Reduces support burden:** Fewer "why doesn't X work?" issues
5. **Industry standard:** Hugo, Django do this

### ❌ CONS: Accept Plurality

1. **Two ways to do it:** Violates "one obvious way" (Python Zen)
2. **Documentation ambiguity:** Which form do we document?
3. **Complexity:** More code to maintain
4. **Hidden magic:** Users may not realize normalization happens
5. **Consistency issues:** Some use `[menu]`, others use `[menus]`

## Decision Matrix

| Criterion | Strict (Singular Only) | Flexible (Accept Both) |
|-----------|------------------------|------------------------|
| **Clarity** | ✅ One way, clear | ⚠️ Two ways, potential confusion |
| **Ergonomics** | ❌ Easy to get wrong | ✅ Forgiving, intuitive |
| **Migration** | ❌ Requires changes | ✅ Works with existing configs |
| **Consistency** | ✅ Everyone uses same form | ⚠️ Different codebases use different forms |
| **Debugging** | ✅ Easy to spot errors | ⚠️ Harder to diagnose (silent normalization) |
| **Error Messages** | ✅ Can provide clear errors | ⚠️ Errors happen after normalization |
| **Code Complexity** | ✅ Simple | ⚠️ More complex |
| **User Happiness** | ⚠️ Frustration with typos | ✅ "It just works!" |

## Recommendation: **FLEXIBLE** with Warnings

Accept both, but **warn** users to help them converge on canonical form:

```python
def _normalize_config(self, config: dict) -> dict:
    """Normalize config with helpful warnings."""
    normalized = {}
    warnings = []
    
    for key, value in config.items():
        canonical = SECTION_ALIASES.get(key)
        
        if canonical and canonical != key:
            # Accept it, but inform user
            warnings.append(
                f"💡 Using [{key}] works, but [{canonical}] is preferred for consistency"
            )
            normalized[canonical] = value
        else:
            normalized[key] = value
    
    # Show warnings (but don't fail)
    if warnings and config.get('verbose'):
        for warning in warnings:
            print(warning)
    
    return normalized
```

### Example Output
```bash
$ bengal build --verbose

💡 Config note: Using [menus] works, but [menu] is preferred for consistency

✅ Built 57 pages...
```

**Benefits:**
- ✅ Works for users (ergonomic)
- ✅ Guides toward best practice (educational)
- ✅ Doesn't break builds (forgiving)
- ✅ Reduces support burden (fewer issues)

## Implementation Strategy

### Phase 1: Add Aliases (Immediate)
```python
SECTION_ALIASES = {
    # Plural → Canonical
    'menus': 'menu',
    
    # Keep taxonomies plural (it's already correct)
    # 'taxonomies': 'taxonomies'  # Already plural
}
```

### Phase 2: Add Config Validation (Next)
```python
def _check_unknown_sections(self, config: dict) -> List[str]:
    """Check for typos and suggest corrections."""
    KNOWN_SECTIONS = {'site', 'build', 'menu', 'taxonomies', ...}
    ALIASES = {'menus': 'menu', ...}
    
    warnings = []
    for key in config.keys():
        if key not in KNOWN_SECTIONS and key not in ALIASES:
            # Unknown section - suggest correction
            suggestions = difflib.get_close_matches(key, KNOWN_SECTIONS)
            if suggestions:
                warnings.append(
                    f"Unknown section [{key}], did you mean [{suggestions[0]}]?"
                )
    
    return warnings
```

### Phase 3: Documentation (Ongoing)
```markdown
## Menu Configuration

Define menus using **`[[menu.name]]`** (singular):

```toml
[[menu.main]]
name = "Home"
url = "/"
```

> **Note:** `[[menus.main]]` also works for Hugo compatibility,
> but `[[menu.main]]` is preferred.
```

## Real-World Example

### User Journey: BEFORE (Strict)
```
User: *writes [[menus.main]]*
Build: ✅ Success (but no menu shows up)
User: "Why isn't my menu working??"
User: *searches docs, finds nothing*
User: *asks on Discord*
Support: "Oh, you need [menu] not [menus]"
User: "😤 Why didn't it tell me that??"
```

**Result:** Frustration, support burden

### User Journey: AFTER (Flexible)
```
User: *writes [[menus.main]]*
Build: ✅ Success (menu works!)
Build: 💡 Tip: [menu] is preferred over [menus]
User: "Oh cool, I'll update that later"
```

**Result:** Success, gentle education

## Edge Cases

### Both Defined
```toml
[[menu.main]]
name = "Home"

[[menus.main]]  # Oops, typo/confusion
name = "About"
```

**Solution:** Merge and warn
```
⚠️  Both [menu] and [menus] defined. Merging into [menu].
    Consider using only [menu] for clarity.
```

### Typos Still Caught
```toml
[[menuz.main]]  # Typo
```

**Solution:** Still suggest correction
```
❌ Unknown section [menuz]. Did you mean [menu]?
```

## Comparison to Other Languages

### Python: Strict but Clear Errors
```python
from os import path    # ✅ Works
from os import paths   # ❌ ImportError: cannot import name 'paths'
```

**Lesson:** Clear errors > silent failures

### HTML: Very Forgiving
```html
<div>                  <!-- ✅ Works -->
<DIV>                  <!-- ✅ Also works (case insensitive) -->
<span />               <!-- ✅ Self-closing works -->
```

**Lesson:** Forgiveness = better adoption

### SQL: Case Insensitive
```sql
SELECT * FROM users;   -- ✅ Works
select * from USERS;   -- ✅ Also works
```

**Lesson:** Technical flexibility reduces errors

## Conclusion

**Recommended Approach: FLEXIBLE with GUIDANCE**

1. ✅ **Accept both** `[menu]` and `[menus]` (and other common variants)
2. ✅ **Normalize** to canonical form internally
3. ✅ **Gentle warnings** in verbose mode to educate
4. ✅ **Document** canonical form as preferred
5. ✅ **Validate** unknown sections to catch real typos

**Rationale:**
- Reduces user frustration (high value)
- Minimal code complexity (low cost)
- Industry precedent (Hugo does this)
- Follows "principle of least surprise"
- Doesn't compromise technical clarity

**Alternative names for this pattern:**
- "Forgiving parsing"
- "Alias normalization"
- "Ergonomic configuration"
- "User-friendly config"

---

## Action Items

- [ ] Implement `SECTION_ALIASES` in `config/loader.py`
- [ ] Add normalization with optional warnings
- [ ] Update config validator to suggest corrections
- [ ] Update documentation to show canonical forms
- [ ] Add tests for alias handling
- [ ] Update health check to validate config sections

**Status:** Recommended for implementation  
**Priority:** Medium (improves UX, prevents confusion)  
**Effort:** Low (2-3 hours)

