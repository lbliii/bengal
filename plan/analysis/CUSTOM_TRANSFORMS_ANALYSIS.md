# Lightning CSS Custom Transforms Analysis

**Date**: October 8, 2025  
**Question**: Should Bengal use Lightning CSS custom transforms/visitors?  
**Answer**: **NO** - Not available in Python, not needed for SSGs

---

## What Are Custom Transforms?

According to the [Lightning CSS transforms docs](https://lightningcss.dev/transforms.html), the visitor API allows:

### JavaScript-Only Feature
```js
// JavaScript Node API only
transform({
  code: Buffer.from('...'),
  visitor: {
    Length(length) {
      return { unit: length.unit, value: length.value * 2 }
    }
  }
});
```

### What It Enables
1. **Custom CSS extensions**
   - Custom shorthand properties
   - Custom at-rules (mixins)
   - Non-standard syntax

2. **Build-time transforms**
   - Unit conversion
   - Constant inlining
   - Value manipulation

3. **CSS analysis**
   - Extract values
   - Validate syntax
   - Collect statistics

---

## Key Limitation: JavaScript Only ❌

### Python Package Doesn't Expose This
```python
import lightningcss

# Available functions:
# - process_stylesheet()
# - calc_parser_flags()

# NOT available:
# - transform() with visitor parameter
# - composeVisitors()
# - Custom visitor API
```

**The Python bindings (v0.2.2) don't expose the visitor API.**

This is a **JavaScript-only feature** in the Node.js bindings.

---

## Performance Warning

From the [docs](https://lightningcss.dev/transforms.html):

> Custom transforms have a build time cost: it can be around **2x slower** to compile with a JS visitor than without. This means visitors should generally be used to implement **custom, non-standard CSS extensions**.

**For Bengal**: Even if we had access, the 2x slowdown would be unacceptable for standard CSS processing.

---

## What Custom Transforms Are For

### ✅ Framework Authors (React/Vue/Svelte)
```js
// Custom JSX-in-CSS syntax
visitor: {
  Function: {
    jsxColor() {
      return { raw: 'rgb(255, 0, 0)' };
    }
  }
}
```

### ✅ CSS-in-JS Libraries
```js
// styled-components, Emotion, etc.
visitor: {
  Property: {
    custom: {
      extend(property) {
        // Handle extends/mixins
      }
    }
  }
}
```

### ✅ Design System Tools
```js
// Convert design tokens at build time
visitor: {
  Token: {
    'at-keyword'(token) {
      return designTokens.get(token.value);
    }
  }
}
```

### ✅ Build Tool Plugins
```js
// Webpack/Vite plugins for custom CSS features
visitor: {
  Rule: {
    custom: {
      mixin(rule) {
        return expandMixin(rule);
      }
    }
  }
}
```

---

## What Bengal Is

### ❌ Not a Framework
- We don't need custom CSS syntax
- We don't need JSX integration
- We don't need CSS-in-JS

### ❌ Not a Design System
- We don't have build-time tokens
- We don't need custom at-rules
- We use standard CSS

### ❌ Not a Build Tool Plugin
- We're the build tool
- We process standard CSS
- We don't add custom syntax

### ✅ We're an SSG
- We bundle standard CSS
- We minify standard CSS
- We autoprefix standard CSS
- **That's all we need!**

---

## Examples of Custom Transforms (From Docs)

### 1. Custom Shorthand Property
```js
// Not useful for SSGs
visitor: {
  Property: {
    custom: {
      size(property) {
        // Expand 'size: 12px' to width + height
        return [
          { property: 'width', value: property.value },
          { property: 'height', value: property.value }
        ];
      }
    }
  }
}
```

**Bengal**: Users can just write `width` and `height`. No need for custom syntax.

### 2. Inline Variables
```js
// Not useful for SSGs
visitor: {
  Token: {
    'at-keyword'(token) {
      return constants.get(token.value);
    }
  }
}
```

**Bengal**: CSS custom properties already do this:
```css
:root { --color: blue; }
.foo { color: var(--color); }
```

### 3. Custom Mixins
```js
// Not useful for SSGs
visitor: {
  Rule: {
    custom: {
      mixin(rule) {
        mixins.set(rule.prelude.value, rule.body);
      },
      apply(rule) {
        return mixins.get(rule.prelude.value);
      }
    }
  }
}
```

**Bengal**:
- CSS already has mixins via classes
- SCSS/SASS if users want preprocessing
- Not our job to add custom syntax

### 4. Unit Conversion
```js
// Might be useful, but...
visitor: {
  Length(length) {
    if (length.unit === 'px') {
      return { unit: 'rem', value: length.value / 16 };
    }
  }
}
```

**Bengal**:
- Users should write what they want
- Automatic conversion is surprising
- Not a common SSG feature

---

## What Bengal Actually Needs (Already Have)

### ✅ Standard CSS Processing
```python
# What we use Lightning CSS for:
lightningcss.process_stylesheet(
    css_content,
    minify=True,              # Minify
    browsers_list=[...],       # Autoprefix
)
```

**This gives us:**
- ✅ Minification (optimizations)
- ✅ Autoprefixing (browser compat)
- ✅ Modern CSS → legacy CSS transforms
- ✅ All built-in, no custom code needed

### ✅ Custom Bundling (We Implemented)
```python
# We added this ourselves
def bundle_imports(css_content, base_path):
    # Resolve @import statements
    # Return bundled CSS
```

**Why custom**: Python package doesn't expose `bundle()` API

---

## If Users Want Custom CSS Syntax

### They Can Use External Tools

**Option 1: SCSS/SASS**
```bash
# User's build script
sass src/styles.scss assets/style.css
bengal build
```

**Option 2: PostCSS**
```bash
# User's build script
postcss src/style.css -o assets/style.css
bengal build
```

**Option 3: Tailwind**
```bash
# User's build script
tailwindcss -i src/input.css -o assets/output.css
bengal build
```

**Bengal doesn't need to support these** - they're preprocessing steps that users can run before Bengal builds the site.

---

## Comparison with Other SSGs

### Hugo
- ❌ No custom transform API
- ✅ Supports SCSS via LibSass
- ✅ Hugo Pipes for asset processing
- 📝 Doesn't try to extend CSS syntax

### Jekyll
- ❌ No custom transform API
- ✅ Supports SCSS via Sass gem
- ✅ Asset pipeline via plugins
- 📝 Preprocessing, not custom syntax

### Gatsby
- ❌ No built-in custom CSS transforms
- ✅ PostCSS plugins via Webpack
- ✅ CSS Modules
- 📝 Uses standard tooling

### Docusaurus
- ❌ No custom CSS transforms
- ✅ PostCSS support
- ✅ CSS Modules
- 📝 Standard React tooling

**Pattern**: SSGs don't add custom CSS syntax. They support standard preprocessors or let users run their own.

---

## When You WOULD Want Custom Transforms

### If Bengal Was...

1. **A CSS Framework**
   ```python
   # If we were like Tailwind
   class BengalCSS:
       def add_directive(self, name, handler):
           self.visitors[name] = handler
   ```

2. **A Design System Builder**
   ```python
   # If we converted design tokens
   visitor = {
       'Token': {
           'design-token': lambda t: tokens.get(t.value)
       }
   }
   ```

3. **A JavaScript Framework**
   ```python
   # If we had JSX/components
   visitor = {
       'Property': {
           'css-prop': lambda p: convert_jsx(p)
       }
   }
   ```

**But we're none of these!**

---

## Technical Limitations

### 1. Python Bindings Don't Support It
The Python `lightningcss` package (v0.2.2) only exposes:
- `process_stylesheet(code, ...)` - Process CSS string
- `calc_parser_flags(...)` - Parser configuration

No visitor API, no `transform()` with visitors, no `composeVisitors()`.

### 2. Would Require JavaScript Bridge
To use visitors from Python, we'd need to:
1. Spawn Node.js process
2. Pass CSS to JavaScript
3. Run Lightning CSS with visitor
4. Get result back
5. Parse in Python

**This is:**
- ❌ Slow (process spawning)
- ❌ Complex (IPC communication)
- ❌ Fragile (two language barrier)
- ❌ Not worth it for standard CSS

### 3. Performance Cost
Even if we could use it:
- 2x slower compilation
- JavaScript overhead
- Serialization cost

**For what?** To add custom CSS syntax that:
- Users don't need
- Isn't standard
- Makes debugging harder

---

## Recommendation: Don't Use Custom Transforms

### Reasons ❌

1. **Not available** - Python package doesn't expose it
2. **Not needed** - We process standard CSS
3. **Performance cost** - 2x slower
4. **Wrong abstraction** - SSGs don't extend CSS syntax
5. **User expectation** - Users expect standard CSS

### What We Have Is Perfect ✅

```python
# Our current approach
bundled_css = bundle_imports(css_content, base_path)
result = lightningcss.process_stylesheet(
    bundled_css,
    minify=True,
    browsers_list=['last 2 Chrome versions', ...],
)
```

**This is:**
- ✅ Standard CSS processing
- ✅ Fast (no JavaScript visitor overhead)
- ✅ Simple (no custom syntax)
- ✅ Predictable (standard behavior)
- ✅ Debuggable (standard CSS output)

---

## If We Ever Add Custom CSS Features

### Don't Use Lightning CSS Visitors

**Instead, implement in Python:**

```python
# Hypothetical: Custom @include directive
def preprocess_css(css_content):
    # Python regex/parser to handle @include
    return process_includes(css_content)

# Then pass to Lightning CSS
result = lightningcss.process_stylesheet(
    preprocess_css(css_content),
    minify=True,
    browsers_list=[...],
)
```

**Why better:**
- ✅ No JavaScript dependency
- ✅ Full control
- ✅ Better performance
- ✅ Easier debugging

**But realistically:** We shouldn't add custom CSS syntax at all.

---

## Future Considerations

### If Python Bindings Add Visitor Support

**Still probably shouldn't use it** because:
1. SSGs shouldn't extend CSS syntax
2. Users can use SCSS/PostCSS externally
3. Performance cost isn't worth it
4. Adds complexity for little benefit

### If Users Request Custom Syntax

**Recommend external preprocessing:**
1. User runs SCSS/PostCSS/Tailwind
2. Output goes to `assets/`
3. Bengal bundles and minifies
4. Clean separation of concerns

---

## Comparison Matrix

| Feature | Custom Transforms | Bengal Current | Verdict |
|---------|-------------------|----------------|---------|
| **Availability** | JS only | Python | ❌ Can't use |
| **Performance** | 2x slower | Fast | ✅ Keep current |
| **Use case** | Custom syntax | Standard CSS | ✅ Don't need it |
| **Complexity** | High | Low | ✅ Keep simple |
| **Debugging** | Harder | Easy | ✅ Keep standard |
| **User expectation** | Surprising | Standard | ✅ Meet expectations |

---

## Final Answer

**Question**: Should we use Lightning CSS custom transforms?

**Answer**: **NO** - for multiple reasons:

1. **Not available** in Python bindings
2. **Not appropriate** for SSGs (wrong abstraction level)
3. **Performance cost** (2x slower)
4. **No user demand** (SSG users expect standard CSS)
5. **Better alternatives** (external SCSS/PostCSS/Tailwind)

**Our current approach is correct:**
- ✅ Bundle @import statements (custom Python code)
- ✅ Minify with Lightning CSS (standard processing)
- ✅ Autoprefix with Lightning CSS (standard processing)
- ✅ Standard CSS in, optimized CSS out

**This is the right level of abstraction for an SSG.** ✅

---

## References

- [Lightning CSS Custom Transforms](https://lightningcss.dev/transforms.html) - JavaScript only
- Python `lightningcss` package - No visitor API
- Hugo, Jekyll, Gatsby - Don't use custom CSS transforms
- Industry standard: SSGs process standard CSS, don't extend syntax

---

**Conclusion**: Custom transforms are for framework authors and build tool plugins, not SSGs. Bengal's approach is correct.
