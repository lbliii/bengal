# Critical Issues from Benchmark

## Issue #1: Incremental Builds Doing Full Rebuilds ⚠️ CRITICAL

**Severity**: Critical - Core feature is broken  
**Impact**: Users get 1.1x speedup instead of 15-50x  
**User Pain**: High - defeats entire purpose of incremental builds

**Symptom**:
```
Running incremental build (single page change)...
Config file changed - performing full rebuild
```

**Root Cause**: Config change detection is triggering when it shouldn't

---

## Issue #2: Performance Collapses at Scale ⚠️ HIGH

**Severity**: High - Limits usability at enterprise scale  
**Impact**: 141 pps → 29 pps (79% slower at 10K pages)  
**User Pain**: Medium - Still faster than Sphinx, but not acceptable

**Symptom**:
- 1K pages: 141 pps (9.4s) ✅
- 5K pages: 71 pps (92s) ⚠️ 50% degradation
- 10K pages: 29 pps (451s) ❌ 79% degradation

**Root Cause**: Unknown - likely O(n²) algorithm or memory pressure

---

## Priority: Fix Issue #1 First

Issue #1 is more critical because:
1. Affects ALL users (not just large sites)
2. Core feature is completely broken
3. Likely easier to fix than Issue #2
4. User specifically asked about speed for their workflow

Let's diagnose and fix the incremental build bug.
