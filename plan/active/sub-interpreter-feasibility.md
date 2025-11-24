# Sub-Interpreter Feasibility Study

**Date**: 2025-01-23  
**Status**: ✅ Available in Python 3.14  
**Priority**: Research

## Discovery

✅ **Sub-interpreters ARE available in Python 3.14!**

```python
import _interpreters
interp_id = _interpreters.create()
# Each sub-interpreter has its own GIL (or no GIL if free-threaded!)
# Can run in parallel even without free-threading
```

**Key Finding**: Sub-interpreters work WITH free-threading!

- **Standard Python 3.14**: Each sub-interpreter has its own GIL → parallelism between interpreters
- **Free-threaded Python 3.14t**: Each sub-interpreter also has NO GIL → true parallelism within AND between interpreters

**Implication**: With free-threading, ThreadPoolExecutor already gives true parallelism. Sub-interpreters would mainly provide **isolation**, not necessarily performance.

**API Status**:
- ✅ Low-level `_interpreters` module: Available
- ❌ High-level `interpreters` module: Not available yet
- ❌ Channels: Not in `_interpreters` module (might be separate or not yet available)

**Available Functions**:
- `create()` - Create sub-interpreter ✅
- `run_string()` - Run code in sub-interpreter ✅
- `run_func()` - Run function in sub-interpreter ✅
- `destroy()` - Destroy sub-interpreter ✅
- `list_all()` - List all interpreters ✅

**Data Sharing Challenge**:
- Channels not available in `_interpreters` module
- Need to research: How to share data between interpreters?
- Options: `CrossInterpreterBufferView`, pickle via `run_func`, or wait for channels API

## Key Questions to Answer

### 1. Performance Comparison

**Question**: Is sub-interpreter rendering faster than ThreadPoolExecutor?

**Test Needed**:
- Benchmark: Parse markdown in sub-interpreter vs thread
- Measure: Channel overhead (data sharing)
- Compare: Total time for 100 pages

**Hypothesis**:
- Sub-interpreters might be faster for CPU-bound work (no GIL contention)
- But channel overhead might negate benefits
- Need to measure!

---

### 2. Data Sharing Efficiency

**Question**: Can we efficiently share Site/Page objects?

**Challenges**:
- Site object is large (all pages, config, assets)
- Page objects need to be sent via channels (pickle)
- Overhead might be significant

**Test Needed**:
- Measure: Pickling overhead for Site/Page
- Measure: Channel send/receive time
- Compare: vs direct object access in threads

**Hypothesis**:
- Pickling Site might be expensive (large object)
- But we could send only what's needed (page content, config subset)
- Need to measure!

---

### 3. Implementation Complexity

**Question**: Is the complexity worth the benefit?

**Current (ThreadPoolExecutor)**:
```python
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(render_page, page) for page in pages]
    results = [f.result() for f in futures]
```

**Sub-Interpreter Approach**:
```python
# Create sub-interpreters
interpreters = [_interpreters.create() for _ in range(max_workers)]

# Create channels for each
channels = [_interpreters.channel.create() for _ in range(max_workers)]

# Send work to sub-interpreters
for i, page in enumerate(pages):
    interp_id = interpreters[i % max_workers]
    ch = channels[i % max_workers]
    # Send page data via channel
    ch.send(pickle.dumps(page))

# Collect results
results = []
for ch in channels:
    result = pickle.loads(ch.recv())
    results.append(result)
```

**Complexity**: Medium-High
- More code
- Channel management
- Error handling more complex
- Need to handle interpreter crashes

---

## Potential Benefits

### 1. True Parallelism (Even Without Free-Threading)

**Current**:
- Python 3.14 (with GIL): Limited parallelism
- Python 3.14t (free-threaded): True parallelism ✅

**With Sub-Interpreters**:
- Python 3.14 (with GIL): True parallelism via sub-interpreters! 🎯
- Python 3.14t (free-threaded): Still true parallelism

**Impact**: Makes Bengal faster even on standard Python 3.14 builds

---

### 2. Better Isolation

**Current**:
- One parser crash can affect other threads
- Shared state can cause issues

**With Sub-Interpreters**:
- Each interpreter is isolated
- One crash doesn't affect others
- Better error recovery

---

### 3. Potential Performance Gain

**Estimated**: 10-20% faster rendering
- No GIL contention (even on standard Python)
- Better CPU utilization
- But: Channel overhead might reduce this

---

## Research Plan

### Phase 1: Basic Feasibility (1-2 hours)

1. ✅ **Verify availability** - DONE (sub-interpreters available)
2. **Test basic markdown parsing**
   ```python
   # Parse markdown in sub-interpreter
   # Measure overhead vs thread
   ```
3. **Test Site/Page pickling**
   ```python
   # Can we pickle Site/Page?
   # What's the overhead?
   ```

### Phase 2: Prototype (2-4 hours)

4. **Create minimal prototype**
   - Simple rendering in sub-interpreter
   - Compare vs ThreadPoolExecutor
   - Measure: speed, memory, complexity

### Phase 3: Decision (Based on Results)

5. **If promising**: Full implementation
6. **If not**: Document why (overhead, complexity, etc.)

---

## Expected Outcomes

**Best Case**:
- 10-20% faster rendering
- Better isolation
- Worth the complexity

**Realistic Case**:
- Channel overhead negates benefits
- Complexity not worth it
- Stick with ThreadPoolExecutor

**Worst Case**:
- Site/Page not efficiently picklable
- Overhead too high
- Not feasible

---

## Next Steps

1. **Create feasibility test** - Measure sub-interpreter overhead
2. **Test pickling** - Can we efficiently share Site/Page?
3. **Benchmark** - Compare vs ThreadPoolExecutor
4. **Decision** - Implement or document why not

---

## References

- [PEP 734: Multiple Interpreters](https://peps.python.org/pep-0734/)
- [Python 3.14 _interpreters module](https://docs.python.org/3.14/library/_interpreters.html)
