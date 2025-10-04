# Fence Nesting Health Check Implementation

**Date:** October 4, 2025  
**Status:** ✅ Complete  
**Feature:** Health check to detect fence nesting issues in directives

---

## 🎯 Problem Statement

When users write directives with nested code blocks, they can inadvertently use the same fence depth (3 backticks) for both, causing parsing issues:

### Bad Example (Broken)
```markdown
```{tabs}
### Tab: Python
```python
print("code")
```
```  ← This closes the DIRECTIVE, not the code block!
```

The directive gets truncated at the first closing fence marker, breaking the content structure.

### Good Example (Works)
```markdown
````{tabs}
### Tab: Python
```python
print("code")
```
````  ← Directive uses 4 backticks, code uses 3
```

---

## ✅ Solution Implemented

Added fence nesting detection to `DirectiveValidator` that:

1. **Detects 3-backtick directives** with nested code blocks
2. **Identifies truncated content** (suspiciously short for tabs/code-tabs)
3. **Warns users** to use 4+ backticks for the directive fence

### Detection Logic

```python
def _check_fence_nesting(directive):
    if fence_depth != 3:
        return  # Only check 3-backtick directives
    
    # Check 1: Direct detection of nested 3-backtick code blocks
    if has_3_backtick_code_blocks:
        warn("Use 4+ backticks for directive")
        return
    
    # Check 2: Detect truncated content (indirect evidence)
    if directive is tabs/code-tabs:
        if content_lines < (tab_count * 3):
            warn("Content appears incomplete - check fence depth")
```

### Health Check Output

```
⚠️ Directives           1 warning(s)
   • 1 directive(s) may have fence nesting issues
     💡 Use 4+ backticks (````) for directive fences when content contains 3-backtick code blocks.
        - example.md:10 - tabs: Content appears incomplete (2 lines, 1 tabs). 
          If tabs contain code blocks, use 4+ backticks (````) for the directive fence.
```

---

## 🧠 Design Insight: `### Tab:` Syntax

During this work, we realized the `### Tab:` syntax is actually **clever design**:

### Why It's Smart

1. **Prevents heading conflicts** - Using H3 for tab delimiters means H3 headings inside tabs would conflict
2. **Forces better structure** - Users must use H4+ for actual headings inside tabs
3. **Separates concerns** - Tab labels are metadata (UI), not content structure
4. **Avoids TOC issues** - Headers in tabs break table of contents and navigation

### The Forcing Function

By "claiming" `### Tab:` syntax, Bengal effectively enforces:
- ✅ Tabs contain content, not structural headings
- ✅ Use H4+ (`####`) for headings within tab content
- ✅ Tab labels are separate from document outline
- ✅ Better accessibility and SEO

This is similar to React using `className` instead of `class` - taking over a keyword to enforce better patterns!

---

## 📊 Testing

### Test Cases

1. **4-backtick directive with 3-backtick code blocks** → ✅ No warning
2. **3-backtick directive with 3-backtick code blocks** → ⚠️ Warning
3. **3-backtick directive with no code blocks** → ✅ No warning
4. **Directive with tab markers but truncated content** → ⚠️ Warning

### Test Results

```bash
$ python test_fence_regex.py

Testing GOOD example (4 backticks):
✅ OK: No fence nesting issues

Testing BAD example (3 backticks):
⚠️ WARNING: Content appears incomplete (2 lines, 1 tabs)
```

---

## 🎨 Alternative: Colon Fences

### Considered But Not Implemented

MyST markdown supports colon fences (`:::``) as an alternative to backticks:

```markdown
:::{tabs}
### Tab: Python
```python
print("code")
```
:::
```

**Pros:**
- Complete separation between code blocks (backticks) and directives (colons)
- No counting backticks ever
- MyST compatibility

**Cons:**
- Mistune doesn't support it natively
- Additional maintenance burden
- Current multi-backtick approach works well
- Very few users encounter the issue (only 1 file in examples uses 4 backticks)

**Decision:** Document the workaround, add health check. Colon fences could be a future enhancement if demand exists.

---

## 📝 Files Changed

1. `bengal/health/validators/directives.py`:
   - Updated `_extract_directives()` to capture fence depth
   - Added `_check_fence_nesting()` method
   - Enhanced `_check_directive_syntax()` to report fence warnings
   - Added `fence_nesting_warnings` to data collection

2. Health check now warns when:
   - 3-backtick directive contains 3-backtick code blocks
   - Tabs/code-tabs directive has suspiciously short content

---

## 🚀 Impact

### User Experience

- ✅ **Catches errors early** - Before users discover broken pages
- ✅ **Clear guidance** - Tells users exactly how to fix (use 4 backticks)
- ✅ **Non-breaking** - Existing content works, just gets helpful warnings
- ✅ **Educational** - Teaches best practices

### Edge Cases Handled

1. Directives without code blocks - no warning
2. Directives with 4+ backticks - no warning
3. Admonitions/dropdowns - less strict checking (they don't typically have tabs)
4. Code blocks using tildes (`~~~`) - also detected

---

## 📚 Documentation Needed

- [ ] Add to health checks documentation
- [ ] Add to directive syntax guide
- [ ] Include example in "Common Pitfalls" section
- [ ] Update kitchen sink with both good/bad examples

---

## 🎯 Future Enhancements

1. **Colon fence support** - If users request MyST compatibility
2. **Auto-fix** - Automatically upgrade fences in content files
3. **IDE integration** - LSP warnings for fence nesting
4. **Better error messages** - Show exact line of problematic code block

---

## ✅ Completion Checklist

- [x] Implement `_check_fence_nesting()` method
- [x] Update directive extraction to capture fence depth
- [x] Add fence nesting warnings collection
- [x] Report warnings in health check output
- [x] Test with good and bad examples
- [x] Clean up temporary test files
- [x] No linting errors
- [x] Document the feature

---

## 💡 Key Takeaway

This feature demonstrates Bengal's commitment to **production-ready quality assurance**. Rather than letting users discover parsing issues in production, we catch them during build and provide clear, actionable guidance.

The fence nesting check is another example of Bengal's unique health check system that sets it apart from other SSGs!

