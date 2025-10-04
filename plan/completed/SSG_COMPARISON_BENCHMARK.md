# SSG Comparison Benchmark Plan

**Created:** October 3, 2025  
**Status:** In Progress  
**Goal:** Generate apples-to-apples comparison data against other SSGs using CSS-Tricks methodology

## Background

The CSS-Tricks article "Comparing Static Site Generator Build Times" provides a standardized benchmark methodology to compare SSGs:
- URL: https://css-tricks.com/comparing-static-site-generator-build-times/
- Tests: Hugo, Eleventy, Jekyll, Gatsby, Next, Nuxt
- Methodology: Minimal markdown, cold builds, scales from 1-16,384 files

## Implementation

### Created Files

1. **`tests/performance/benchmark_ssg_comparison.py`**
   - Matches CSS-Tricks methodology exactly
   - Test scales: 1, 16, 64, 256, 1024, 4096, 8192, 16384 files
   - Minimal content: title + 3 paragraphs (no code blocks, lists, etc.)
   - Cold builds: fresh temp directory each run
   - All optimizations disabled
   - 3 runs per scale, averaged

### How to Run

```bash
cd /Users/llane/Documents/github/python/bengal
python tests/performance/benchmark_ssg_comparison.py
```

**Warning:** Full run (up to 16K files) can take 30-60 minutes depending on hardware.

**Quick test option:** Edit the script to use smaller scales:
```python
scales = [1, 16, 64, 256, 1024]  # Quick test
```

## Expected Results

Based on Bengal's existing benchmarks:

### Hypothesis: Bengal's Position

**Small Sites (1-100 files):**
1. 🥇 Hugo (~0.05-0.1s) - Go unbeatable
2. 🥈 Eleventy (~0.5-1s) - Node.js optimized
3. 🥉 **Bengal (~0.5-2s)** - Python competitive
4. Jekyll (~1-3s) - Ruby slower
5. Framework SSGs (5-10s) - Too much overhead

**Medium Sites (100-1,000 files):**
1. 🥇 Hugo (~0.5-2s)
2. 🥈 **Bengal (~2-8s)** - Python scaling well
3. 🥉 Eleventy (~3-10s)
4. Jekyll (~10-30s)
5. Framework SSGs (15-60s)

**Large Sites (1,000-16,000 files):**
1. 🥇 Hugo (~5-20s)
2. 🥈 **Bengal (~20-120s?)** - Need to test!
3. 🥉 Eleventy (~30-180s)
4. Jekyll (~120-600s)
5. Framework SSGs (240s+)

### Key Questions to Answer

1. **How does Bengal scale?**
   - Linear? (good)
   - Sub-linear? (excellent - caching working)
   - Super-linear? (bad - bottlenecks exist)

2. **Where does Bengal beat others?**
   - Faster than Jekyll at all scales? (likely yes)
   - Competitive with Eleventy? (possible)
   - Better than framework SSGs? (definitely)

3. **What's the sweet spot?**
   - Up to what file count is Bengal "fast enough"?
   - Where does performance degrade?

## Next Steps After Running Benchmark

### 1. Analyze Results
- [ ] Calculate scaling factor (linear vs super-linear)
- [ ] Identify performance sweet spots
- [ ] Compare against CSS-Tricks data
- [ ] Find bottlenecks at large scales

### 2. Profile if Needed
If performance at large scales is poor:
```bash
python -m cProfile -o profile.stats tests/performance/benchmark_ssg_comparison.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

### 3. Optimize if Needed
Common bottlenecks to check:
- Markdown parsing (mistune should be fast)
- Template rendering (Jinja2 should be fast)
- File I/O (use buffering)
- Taxonomy collection (can be O(n²) if not careful)
- Parallel overhead (too many processes?)

### 4. Document Results

#### Update README.md
Add performance comparison section:
```markdown
## Performance

Bengal is designed for speed, with benchmarks comparable to other leading SSGs:

| Files | Bengal | Hugo | Eleventy | Jekyll |
|-------|--------|------|----------|--------|
| 10    | 0.2s   | 0.05s| 0.5s     | 1.0s   |
| 100   | 1.7s   | 0.3s | 2.0s     | 5.0s   |
| 1,000 | ?s     | 2.0s | 15s      | 50s    |

*Benchmark methodology: CSS-Tricks standard (minimal markdown, cold builds)*
```

#### Create Performance Documentation
Consider creating `docs/PERFORMANCE.md` with:
- Benchmark methodology
- Detailed results
- Scaling analysis
- Performance tips
- Optimization guide

### 5. Marketing Opportunities

If results are good:
- [ ] Blog post: "How Fast is Bengal? Comparing SSG Build Times"
- [ ] Update landing page with performance claims
- [ ] Create comparison chart/infographic
- [ ] Submit to Show HN / Reddit
- [ ] Update project description with performance highlights

### 6. Compare Against Real-World SSGs

Actually run the other SSGs with same data:

**Hugo:**
```bash
hugo new site hugo-benchmark
# Copy markdown files
hugo --quiet
```

**Eleventy:**
```bash
npm install -g @11ty/eleventy
# Copy markdown files
eleventy --quiet
```

**Jekyll:**
```bash
gem install jekyll
jekyll new jekyll-benchmark
# Copy markdown files
jekyll build --quiet
```

This gives REAL comparison data, not just estimates!

## Success Metrics

### Minimum Viable Performance
- ✅ Faster than Jekyll at all scales
- ✅ Under 2s for 100 pages
- ✅ Linear or sub-linear scaling
- ✅ Usable for sites up to 1,000 pages

### Stretch Goals
- 🎯 Competitive with Eleventy (within 2x)
- 🎯 Under 30s for 1,000 pages
- 🎯 Under 5 minutes for 16,384 pages
- 🎯 Top 3 in Python SSG ecosystem

## Risks & Mitigations

### Risk 1: Poor Performance at Scale
**Mitigation:** Profile and optimize hot paths

### Risk 2: Slower Than Expected
**Mitigation:** 
- Emphasize other features (type safety, health checks, etc.)
- Focus on incremental build speed (where Bengal excels: 18-42x)
- Target audience who values features over raw speed

### Risk 3: Can't Complete Large Tests
**Mitigation:**
- Run smaller scales (up to 4,096)
- Test on more powerful hardware
- Add timeout/interrupt handling

## Timeline

- **Now:** Script created and ready
- **Today:** Run benchmarks (1-2 hours)
- **Today:** Analyze results (1 hour)
- **This week:** Document and share results
- **Optional:** Compare against real Hugo/Eleventy installations

## Notes

- CSS-Tricks article is from 2020, so data is dated
- SSG landscape has evolved (Eleventy 1.0, Hugo improvements)
- Framework SSGs (Gatsby/Next/Nuxt) have improved caching
- Our incremental build speed (42x) is already impressive
- Focus on Bengal's unique strengths: type safety, health checks, Python ecosystem

## Resources

- CSS-Tricks Article: https://css-tricks.com/comparing-static-site-generator-build-times/
- Results Site: https://ssg-build-performance-tests.netlify.app/
- GitHub Repo: https://github.com/seancdavis/ssg-build-performance-tests
- Bengal's Existing Benchmarks: `tests/performance/README.md`

