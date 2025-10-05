# Manual Test: Dev Server Incremental Builds

**Date**: October 5, 2025  
**Change**: Enable `incremental=True` and `parallel=True` in dev server file watch

## Test Checklist

### ✅ Test 1: Single File Change
```bash
cd examples/showcase
bengal serve

# In another terminal:
echo "# Test change $(date +%s)" >> content/index.md

# Expected: Rebuild in < 0.5s (was ~1.2s before)
# Verify: Page updates correctly in browser
```

**Results**:
- [ ] Rebuild time: _____ seconds
- [ ] Page updated correctly: Yes / No
- [ ] No errors: Yes / No

---

### ✅ Test 2: Multiple Rapid Changes
```bash
# Dev server running...

# Rapidly edit multiple files
for i in 1 2 3; do
  echo "# Edit $i $(date +%s)" >> content/features/feature-$i.md
  sleep 0.2
done

# Expected: Builds queue, execute sequentially
# Verify: All changes reflected, no crashes
```

**Results**:
- [ ] No crashes: Yes / No
- [ ] All changes reflected: Yes / No
- [ ] Lock prevented concurrent builds: Yes / No

---

### ✅ Test 3: Config Changes (Full Rebuild)
```bash
# Dev server running...

# Edit config file
echo "\n# Test comment" >> bengal.toml

# Expected: Full rebuild triggered (config change detected)
# Verify: Message shows "Config file changed - performing full rebuild"
```

**Results**:
- [ ] Full rebuild triggered: Yes / No
- [ ] Config change detected: Yes / No
- [ ] All pages updated: Yes / No

---

### ✅ Test 4: Template Changes
```bash
# Dev server running...

# Edit a template
echo "<!-- test comment -->" >> themes/default/templates/page.html

# Expected: Affected pages rebuilt
# Verify: Changes visible in browser
```

**Results**:
- [ ] Template change detected: Yes / No
- [ ] Pages updated: Yes / No
- [ ] Changes visible: Yes / No

---

### ✅ Test 5: Error Handling
```bash
# Dev server running...

# Introduce a template error
# (Edit themes/default/templates/page.html and add: {{ undefined_var }})

# Expected: Readable error message
# Verify: Server doesn't crash, error is clear
```

**Results**:
- [ ] Server continues running: Yes / No
- [ ] Error message clear: Yes / No
- [ ] Subsequent edits work: Yes / No

---

### ✅ Test 6: Asset Changes
```bash
# Dev server running...

# Edit CSS file
echo "/* test styles */" >> themes/default/assets/css/main.css

# Expected: Asset reprocessed
# Verify: Changes visible (may need browser cache clear)
```

**Results**:
- [ ] Asset change detected: Yes / No
- [ ] Asset reprocessed: Yes / No
- [ ] Changes visible: Yes / No

---

## Performance Comparison

### Before (parallel=False, incremental=False)
- Single file change: ~1.2s
- Config change: ~1.2s
- Template change: ~1.2s

### After (parallel=True, incremental=True)
- Single file change: _____ s (Expected: < 0.5s)
- Config change: _____ s (Expected: ~1.2s, same as before)
- Template change: _____ s (Expected: variable, depends on affected pages)

**Speedup for single file**: _____x

---

## Issues Found

**Issue 1**:
- Description: 
- Severity: Critical / Major / Minor
- Workaround:

**Issue 2**:
- Description:
- Severity: Critical / Major / Minor
- Workaround:

---

## Overall Assessment

- [ ] ✅ Ready to merge (all tests passed, significant speedup)
- [ ] ⚠️ Needs fixes (list issues above)
- [ ] ❌ Revert (critical issues found)

**Recommendation**: _____

**Notes**: _____

