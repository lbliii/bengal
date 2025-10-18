# URL Ergonomics Analysis: Developer Experience

**Date**: 2025-10-18  
**Context**: Evaluating whether `| absolute_url` requirement is intuitive for theme developers  
**Related**: `url-strategy-downstream-impact.md`

## Current State: Manual Filter Pattern

### What Theme Developers Must Do

```jinja2
{# REQUIRED for all href attributes #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>

{# ALLOWED for comparisons #}
{{ 'active' if page.url == item.url else '' }}
```

### The Mental Model

**Theme developers must understand**:
1. URLs in data structures are "identity URLs" (relative)
2. URLs in `href` attributes need baseurl applied
3. Apply `| absolute_url` filter for display
4. Don't apply filter for comparisons

## Is This Intuitive?

### ❌ **Cons - Pain Points**

1. **Easy to Forget**
   - Forgetting `| absolute_url` doesn't break local dev
   - Only breaks in production with subpath deployments
   - Silent failure - links work but point to wrong place

2. **Cognitive Load**
   - "Why do some URLs need filter and others don't?"
   - Must remember: display = filter, comparison = no filter
   - Not obvious from the data structure itself

3. **Inconsistent with Intuition**
   - Natural expectation: "If I have a URL, I should be able to use it"
   - Feels like a framework leakage ("why do I care about baseurl?")

4. **Verbose**
   - `| absolute_url` adds 16 characters to every link
   - Clutters templates

### ✅ **Pros - What Works**

1. **Explicit is Better Than Implicit**
   - Clear when baseurl is being applied
   - No magic/hidden transformations
   - Grep-able: can search for `absolute_url` usage

2. **Follows Jinja Conventions**
   - Filters are standard Jinja pattern
   - Similar to `| safe`, `| escape`, `| url_encode`

3. **Flexible**
   - Template authors can choose when to apply baseurl
   - Supports edge cases (relative links, anchors, etc.)

## How Other SSGs Handle This

### **Hugo** (Go Templates)

```go-template
{{/* Automatic baseurl application in most contexts */}}
<a href="{{ .Permalink }}">{{ .Title }}</a>  {{/* Includes baseurl */}}
<a href="{{ .RelPermalink }}">{{ .Title }}</a>  {{/* Without baseurl */}}

{{/* Manual application when needed */}}
<a href="{{ "about" | absURL }}">About</a>
```

**Hugo's approach**:
- Provides BOTH: `.Permalink` (absolute) and `.RelPermalink` (relative)
- Default to absolute URLs in most contexts
- Manual filter only for string paths

**Ergonomics**: ⭐⭐⭐⭐⭐ Excellent - sensible defaults

### **Jekyll** (Liquid)

```liquid
<!-- Automatic baseurl via site config -->
<a href="{{ site.baseurl }}{{ page.url }}">{{ page.title }}</a>

<!-- Or use relative_url filter -->
<a href="{{ page.url | relative_url }}">{{ page.title }}</a>
```

**Jekyll's approach**:
- `relative_url` filter applies baseurl
- Named "relative_url" (confusing - it actually makes it absolute with baseurl!)
- Theme authors concatenate `site.baseurl` manually or use filter

**Ergonomics**: ⭐⭐⭐ Good but confusing naming

### **Eleventy** (Multiple template engines)

```nunjucks
{# Manual concatenation or filter #}
<a href="{{ site.url }}{{ page.url }}">{{ page.title }}</a>

{# Or use url filter #}
<a href="{{ page.url | url }}">{{ page.title }}</a>
```

**Eleventy's approach**:
- `url` filter (shorter name!)
- Can also concatenate manually
- Flexible but requires awareness

**Ergonomics**: ⭐⭐⭐⭐ Good - short filter name

### **Gatsby/Next.js** (React/JS)

```jsx
// Framework handles URLs automatically
<Link href="/about">About</Link>

// baseurl configured in build system
```

**Modern JS framework approach**:
- Framework components handle URLs automatically
- Developer rarely thinks about baseurl

**Ergonomics**: ⭐⭐⭐⭐⭐ Excellent - transparent

## Bengal's Current Pattern

```jinja2
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>
```

**Ergonomics**: ⭐⭐⭐ Good but verbose

**Compared to others**:
- More explicit than Hugo (Hugo provides both .Permalink and .RelPermalink)
- Similar to Eleventy but longer filter name
- More manual than Jekyll's concatenation option

## Can We Do Better?

### **Option 1: Hugo's Dual Property Pattern**

Provide both relative and absolute URL properties:

```python
# On Page/Section objects
page.url          # → "/about/"  (relative, for comparisons)
page.permalink    # → "/repo/about/"  (with baseurl, for display)
```

**Templates become**:
```jinja2
{# Simple and intuitive #}
<a href="{{ item.permalink }}">{{ item.title }}</a>

{# Comparisons use relative #}
{{ 'active' if page.url == item.url else '' }}
```

**Impact Analysis**:
- ✅ More intuitive - just use the right property
- ✅ Self-documenting - name tells you what it does
- ✅ No filters needed for common case
- ⚠️ Adds property to every Page/Section object
- ⚠️ Cache invalidation - permalink depends on baseurl config
- ⚠️ Navigation functions would need to return both?

### **Option 2: Shorter Filter Name**

```jinja2
{# Current #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>

{# Shorter (following Eleventy) #}
<a href="{{ item.url | url }}">{{ item.title }}</a>

{# Even shorter (custom) #}
<a href="{{ item.url | abs }}">{{ item.title }}</a>
```

**Impact**:
- ✅ Less verbose
- ✅ Easy to implement (alias the filter)
- ⚠️ Less explicit about what it does
- ❌ Doesn't solve "easy to forget" problem

### **Option 3: Context-Aware URL Function**

```jinja2
{# URL function that's smart about context #}
<a href="{{ url(item) }}">{{ item.title }}</a>

{# Or as a filter #}
<a href="{{ item | url }}">{{ item.title }}</a>
```

**Impact**:
- ✅ Simple and clean
- ✅ Can handle page objects, strings, etc.
- ⚠️ Less explicit - magic happening
- ⚠️ Harder to grep/search

### **Option 4: Template Auto-Processing (Advanced)**

Hook into Jinja's rendering to auto-apply baseurl to `href` attributes:

```jinja2
{# Framework automatically transforms href attributes #}
<a href="{{ item.url }}">{{ item.title }}</a>
{# ↓ Automatically becomes ↓ #}
<a href="/repo/about/">{{ item.title }}</a>
```

**Impact**:
- ✅ Zero cognitive load
- ✅ "Just works"
- ❌ Magic behavior - hard to debug
- ❌ Performance overhead
- ❌ Could break edge cases
- ❌ Might conflict with external URLs

## Recommendation: Option 1 (Hugo Pattern) + Option 2 (Short Alias)

### **Implementation**

1. **Add `.permalink` property to Page/Section**
   ```python
   @cached_property
   def permalink(self) -> str:
       """Get URL with baseurl applied (for display)."""
       baseurl = self._site.config.get("baseurl", "") if self._site else ""
       return apply_baseurl(self.url, baseurl)
   ```

2. **Keep existing filter but add short alias**
   ```python
   env.filters.update({
       "absolute_url": absolute_url_with_site,
       "url": absolute_url_with_site,  # Short alias
   })
   ```

3. **Update navigation functions to return both**
   ```python
   {
       "url": "/about/",  # Identity (for comparisons)
       "permalink": "/repo/about/",  # Display (for href)
       "title": "About"
   }
   ```

### **Migration Path**

**Phase 1**: Add `.permalink` property
- Pages/sections get `.permalink` property
- Backward compatible - existing code keeps working
- Document new pattern

**Phase 2**: Update templates gradually
```jinja2
{# Old way (still works) #}
<a href="{{ item.url | absolute_url }}">{{ item.title }}</a>

{# New way (recommended) #}
<a href="{{ item.permalink }}">{{ item.title }}</a>

{# Or with short filter #}
<a href="{{ item.url | url }}">{{ item.title }}</a>
```

**Phase 3**: Theme documentation update
- Show `.permalink` as primary pattern
- Mention filter as alternative
- Explain when to use which

### **Template Ergonomics Comparison**

| Pattern | Keystrokes | Intuitiveness | Learning Curve |
|---------|-----------|---------------|----------------|
| Current: `{{ item.url \| absolute_url }}` | 31 | ⭐⭐⭐ | Medium |
| Hugo-style: `{{ item.permalink }}` | 21 | ⭐⭐⭐⭐⭐ | Low |
| Short filter: `{{ item.url \| url }}` | 21 | ⭐⭐⭐⭐ | Low-Med |
| Raw: `{{ item.url }}` (broken!) | 15 | ⭐⭐⭐⭐⭐ | None (but breaks!) |

## Learning Curve Analysis

### **Current System**

**Learning required**:
1. Understand baseurl concept
2. Know when URLs need baseurl (display) vs when they don't (comparison)
3. Remember to apply `| absolute_url` filter
4. Debug when you forget (silent failure in production)

**Time to proficiency**: ~2 hours + 1 production bug

### **With .permalink Pattern**

**Learning required**:
1. Understand baseurl concept
2. Know: `page.url` = relative, `page.permalink` = absolute
3. Use `.permalink` for links (intuitive)
4. Use `.url` for comparisons (intuitive)

**Time to proficiency**: ~30 minutes

### **Is Some Learning Curve Okay?**

**YES, but it should be about concepts, not mechanics**:

✅ **Good learning curve**:
- "Understand that sites can be deployed to subpaths"
- "Know the difference between identity and display URLs"
- "Choose the right property for your use case"

❌ **Bad learning curve**:
- "Remember to apply this magic filter everywhere"
- "Understand why your links broke in production but worked locally"
- "Debug why menu isn't activating (forgot filter in comparison)"

## Conclusion

The current `| absolute_url` pattern is:
- ✅ Functional and correct
- ⭐⭐⭐ Adequate ergonomics
- ⚠️ Easy to forget (footgun)
- 📚 Steeper learning curve than necessary

**Recommended improvement**:
1. Add `.permalink` property (Hugo pattern)
2. Add `| url` filter alias (shorter)
3. Keep `| absolute_url` for backward compatibility
4. Document best practices clearly

**This makes the easy thing easy while keeping the system flexible.**

## Next Steps

- [ ] Implement `.permalink` property on Page
- [ ] Implement `.permalink` property on Section  
- [ ] Add `| url` filter alias
- [ ] Update navigation functions to include permalink
- [ ] Update default theme to use `.permalink` pattern
- [ ] Add migration guide for theme developers
- [ ] Update documentation with ergonomics best practices
