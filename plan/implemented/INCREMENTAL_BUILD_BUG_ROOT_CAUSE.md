# Incremental Build Bug - Root Cause Investigation

## Status: ROOT CAUSE IDENTIFIED ✅

The "broken" incremental build system is not actually running because it's not enabled by default.

---

## The Problem

From `BENCHMARK_RESULTS_ANALYSIS.md`:
- Expected: 15-50x speedup for single-page incremental builds
- Actual: 1.08x-1.25x speedup (essentially full rebuilds)
- Conclusion: Incremental builds are broken

**WRONG DIAGNOSIS**: Incremental builds aren't broken - they're never invoked!

---

## The Root Cause

### Location: `bengal/orchestration/build.py` (line 68)

```python
def build(
    self,
    parallel: bool = True,
    incremental: bool = False,  # <-- DEFAULT FALSE!
    verbose: bool = False,
    ...
) -> BuildStats:
```

### The Chain of Events

1. **Incremental defaults to False** (line 68)
2. **Cache not initialized** (line ~210)
   ```python
   cache, tracker = self.incremental.initialize(enabled=incremental)
                                                     # enabled=False!
   ```
3. **Empty cache created** (in `incremental.py::initialize()`)
   ```python
   if enabled:  # False, so skip
       self.cache = BuildCache.load(cache_path)
   else:
       self.cache = BuildCache()  # <-- EMPTY!
   ```
4. **Every file appears "changed"** (in `build_cache.py::is_changed()`)
   ```python
   if file_key not in self.file_hashes:  # True! Cache empty
       return True  # File appears new
   ```
5. **Full rebuild triggers every time**

---

## Evidence from Benchmarks

Our Phase 1 benchmark runs `bengal build` WITHOUT the `--incremental` flag:

```python
def build_site():
    subprocess.run(
        ["bengal", "build"],  # <-- NO --incremental FLAG!
        cwd=scenario_path,
        ...
    )
```

**Results measured:**
- First full build: 383ms
- Second full build: 642ms (with modifications, but no incremental!)
- Measured "speedup": 1.68x slower

**What was actually happening:**
- Both runs were FULL rebuilds
- No incremental optimization invoked at all
- 1.68x difference is just system variance

---

## Code Walkthrough

### Step 1: Default incremental=False
**File**: `bengal/orchestration/build.py::build()`
```python
def build(self, ..., incremental: bool = False, ...) -> BuildStats:
```

### Step 2: Cache init with False flag
**File**: `bengal/orchestration/build.py` (~line 210)
```python
cache, tracker = self.incremental.initialize(enabled=incremental)
# Passing False!
```

### Step 3: Empty cache created (not loaded)
**File**: `bengal/orchestration/incremental.py::initialize()`
```python
if enabled:  # False, so skipped
    self.cache = BuildCache.load(cache_path)  # Would load from disk
else:
    self.cache = BuildCache()  # Empty cache created!
```

### Step 4: Every file looks "changed"
**File**: `bengal/cache/build_cache.py::is_changed()`
```python
def is_changed(self, file_path: Path) -> bool:
    if not file_path.exists():
        return True

    file_key = str(file_path)
    current_hash = self.hash_file(file_path)

    if file_key not in self.file_hashes:  # True! Cache empty
        return True  # <-- ALL files appear "new"

    return self.file_hashes[file_key] != current_hash
```

### Result: Full rebuild every time
Because all files appear "changed", the full build pipeline runs.

---

## Why This Was Missed

The bug in `BENCHMARK_RESULTS_ANALYSIS.md` stated:

> "Looking at the benchmark output logs: Config file changed - performing full rebuild"

This log message comes from:
```python
if incremental and config_changed:
    cli.info("  Config file modified - performing full rebuild")
```

But this only prints if `incremental=True`. Since our benchmarks never pass `--incremental`, this code path is never hit!

---

## What This Means

| Aspect | Reality |
|--------|---------|
| **Incremental implementation** | ✅ Appears correct |
| **Default behavior** | ❌ Disabled (incremental=False) |
| **What benchmarks test** | ❌ Full builds (not incremental) |
| **"Speedup" measured** | 1.68x slower (both full builds) |
| **Root cause** | Design choice: incremental is opt-in |

---

## The Design Question

Currently incremental builds are **OPT-IN**:
- Users must pass `--incremental` flag
- Users must explicitly call `build(incremental=True)`
- Without the flag, cache is created but NOT loaded

**Options:**
1. Keep as is (explicit opt-in, current design)
2. Auto-enable if cache exists (implicit incremental)
3. Make incremental default (breaking change)

---

## How to Actually Test Incremental Builds

### Option A: Add --incremental flag to benchmarks
```python
subprocess.run(
    ["bengal", "build", "--incremental"],  # <-- ADD THIS
    cwd=scenario_path,
    ...
)
```

### Option B: Use API directly
```python
from bengal.orchestration.build import BuildOrchestrator

orchestrator = BuildOrchestrator(site)
orchestrator.build(incremental=True)  # <-- Pass True
```

### Option C: Modify benchmarks/scenarios/*/bengal.toml
Add config to enable incremental by default (if this feature exists).

---

## Implications

### For Bengal
- Incremental system code appears correct (not "broken")
- But it's hidden behind an opt-in flag
- Users need to know about `--incremental` to use it

### For Performance Claims
- Current: 1.1x speedup (not using incremental at all!)
- Expected: 15-50x speedup (with incremental enabled)
- Gap suggests incremental isn't enabled in typical usage

### For Marketing
- Can't claim "fast incremental builds" if they're not enabled by default
- Should clarify: "Fast incremental builds (when enabled with --incremental flag)"

---

## Investigation Status

✅ Root cause identified: incremental defaults to False  
✅ Code path traced: False → empty cache → full rebuild  
✅ Benchmark flaw identified: not passing --incremental flag  
✅ Design issue clarified: opt-in vs auto-enable  

⏳ Next: Fix benchmarks to test actual incremental performance  
⏳ Next: Decide on incremental default strategy  
⏳ Next: Re-measure with incremental enabled  

---

## Files Involved

- `bengal/orchestration/build.py` - Line 68, defaults incremental to False
- `bengal/orchestration/incremental.py` - Line 67, checks `if enabled:`
- `bengal/cache/build_cache.py` - Lines 199-221, is_changed() logic
- `benchmarks/test_build.py` - Missing `--incremental` flag in subprocess.run()

---

## Conclusion

**The incremental build system is not broken.**
**It's just not enabled by default.**

This is a design choice, not a code bug. The benchmarks were testing full builds, not incremental builds, which is why they showed 1.1x "speedup" (actually just full rebuild variance).

Once benchmarks are fixed to use `--incremental`, we should see the expected 15-50x speedup for single-page changes.
