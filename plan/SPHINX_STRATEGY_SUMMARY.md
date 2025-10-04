# Sphinx Strategy: Executive Summary

**TL;DR**: You're 85% of the way to beating Sphinx. The missing 15% is Python autodoc. That's 4 weeks of work.

---

## The Gap Analysis

### ✅ Already Better Than Sphinx (7/9 areas)
- **Onboarding**: Markdown + TOML vs RST + conf.py
- **Performance**: 10x faster builds, 18-42x incremental
- **Diagnostics**: Health checks vs cryptic errors
- **Content Model**: Taxonomies, pagination vs rigid toctree
- **Dev Experience**: Hot reload server vs nothing
- **Templates**: 75+ functions vs basic Jinja
- **SEO**: Built-in sitemap/RSS vs manual

### ❌ Missing vs Sphinx (2/9 areas)
- **Autodoc**: Python API doc generation (CRITICAL)
- **Versioning**: Multi-version docs support (Important)

---

## The 4-Week Path to Competitive

### Week 1-2: AST-Based Autodoc
```python
# Core insight: Don't import code, parse it
class PythonAPIExtractor:
    """Extract API docs via AST - no imports needed."""
    
    def extract_module(self, path: Path) -> ModuleDoc:
        tree = ast.parse(path.read_text())
        return self._walk_ast(tree)
```

**Better than Sphinx because**:
- ✅ No import errors in CI
- ✅ No `autodoc_mock_imports` hacks
- ✅ Works with type hints (modern Python)
- ✅ Fast (no code execution)
- ✅ Reliable (no environment issues)

### Week 3: Versioned Docs + Theme
- Multi-version build system
- Version switcher UI
- API documentation theme preset
- Canonical URL management

### Week 4: Migration Tool
```bash
$ bengal migrate --from-sphinx

🔍 Analyzing Sphinx project...
   ✓ Found conf.py
   ✓ Found 127 .rst files

🔄 Converting...
   ✓ Config migrated (bengal.toml)
   ✓ Content converted (127 files)

✅ Migration complete in 2 minutes!
```

---

## Why This Wins

### The Market Reality
- Sphinx has **zero love**, only **network effects**
- Developers tolerate it because no alternative has autodoc
- MkDocs proved Markdown is viable (but lacks autodoc)
- You can be "MkDocs + autodoc"

### The Compelling Narrative

> **Sphinx users spend 5 hours fighting tools, 30 minutes writing docs.**
> 
> Bengal flips that: 5 minutes setup, 5 hours writing great docs.

### The Technical Advantage

| Problem | Sphinx Solution | Bengal Solution |
|---------|----------------|-----------------|
| API docs | Import code (fragile) | Parse AST (reliable) |
| Slow builds | No caching | 18-42x incremental |
| Bad errors | Stack traces | Health checks + hints |
| Complex config | 200-line conf.py | 15-line bengal.toml |

---

## ROI Analysis

### Time Investment
- **4 weeks** of development
- **1 week** of polish + launch
- **Total**: 5 weeks

### Market Opportunity
- **50,000+** Python packages on PyPI with docs
- **80%** use Sphinx (frustrated but locked in)
- **Switching friction**: Migration tool reduces to near-zero

### Competitive Moat
1. **First mover**: No one else doing "Hugo for Python docs"
2. **Technical**: AST-based autodoc is genuinely better
3. **Integration**: Already have all the other pieces

---

## The 5-Week Roadmap

```
[Week 1-2] Core Autodoc
  - AST parser for functions/classes/modules
  - Google/NumPy/Sphinx docstring styles
  - Type hint extraction
  - Basic API page generation

[Week 3] Advanced Features
  - Multi-version documentation
  - API docs theme preset
  - Cross-reference system

[Week 4] Migration Path
  - Sphinx migration CLI tool
  - RST → Markdown conversion
  - conf.py → bengal.toml mapping

[Week 5] Launch
  - Documentation site
  - Comparison demos
  - Show HN / Reddit / Python Weekly
  - Find 3-5 early adopters
```

---

## Success Criteria

### 6 Months
- ✅ 100 GitHub stars
- ✅ 50 projects using Bengal
- ✅ 10 migration case studies

### 12 Months  
- ✅ 1,000 stars
- ✅ 500 projects
- ✅ 1+ popular library (10K+ stars) migrated
- ✅ "Recommended for Python docs"

---

## Risk Assessment

### ✅ Low Risk
- **Technical**: AST parsing is well-understood
- **Market**: Clear pain point, frustrated users
- **Competition**: Sphinx innovates slowly
- **Resources**: 5 weeks is achievable

### ⚠️ Manageable Risks
- **Feature gap**: Sphinx has 15 years of edge cases
  - *Mitigation*: Focus on 80% use case, iterate
- **Ecosystem lock-in**: Projects deeply invested
  - *Mitigation*: Make migration trivial
- **Community resistance**: Python community conservative
  - *Mitigation*: Show, don't tell. Real demos.

---

## The Strategic Insight

**Sphinx isn't good—it's just the only option with autodoc.**

Remove that moat by shipping AST-based autodoc, and suddenly:
- 10x faster builds matter
- Better error messages matter  
- Markdown vs RST matters
- Dev server matters

**You're not competing with Sphinx on features.**

**You're competing with the *pain* of using Sphinx.**

And you win that fight easily.

---

## Recommendation

### ✅ Do This
1. **Ship autodoc** (4 weeks) - removes the only blocker
2. **Ship migration tool** (1 week) - removes switching friction
3. **Launch hard** - Show HN, Python Weekly, real demos
4. **Support early adopters** - Make them successful, they'll evangelize

### ❌ Don't Do This
- ❌ Feature creep (keep scope tight)
- ❌ Perfect before launch (ship 80%, iterate)
- ❌ Multi-language support (Python first)
- ❌ Custom search (let users integrate their own)

---

## The Pitch (For Users)

> **Tired of fighting Sphinx?**
> 
> Bengal gives you Python API docs without the pain.
> 
> - ✅ **No import gymnastics**: AST-based extraction
> - ✅ **No conf.py**: Simple TOML configuration  
> - ✅ **No slow builds**: 10x faster with incremental caching
> - ✅ **No cryptic errors**: Helpful diagnostics
> 
> Migrate from Sphinx in 5 minutes:
> ```bash
> $ bengal migrate --from-sphinx
> $ bengal build
> ```
> 
> Same API docs. 10x better experience.

---

## Next Steps

1. **Review strategy**: Does this align with goals?
2. **Validate market**: Talk to 5 Sphinx users about pain points
3. **Prototype autodoc**: 2-day spike to validate AST approach
4. **Commit**: If validation succeeds, commit to 5-week plan
5. **Ship**: Launch v0.3.0 "API Documentation Release"

---

## The Bottom Line

**You have a rare opportunity:**

1. **Clear market need**: Frustrated Sphinx users
2. **Technical advantage**: AST > import-based
3. **Strong foundation**: 85% already built
4. **Achievable scope**: 5 weeks of focused work

**The only question is: Do you want to own Python documentation in 2025?**

If yes, build autodoc. The rest takes care of itself.

---

*See `SPHINX_COMPETITIVE_STRATEGY.md` for detailed analysis and implementation plan.*

