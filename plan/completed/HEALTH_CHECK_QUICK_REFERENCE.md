# Health Check System - Quick Reference

**Last Updated**: October 9, 2025

---

## Current Validators (10)

### ✅ Phase 1: Basic Checks
| Validator | Speed | What It Checks | Status |
|-----------|-------|----------------|--------|
| **Configuration** | ~1ms | Config validity, essential fields, common issues | ✅ Complete |
| **Output** | ~10ms | Page sizes, assets present, directory structure | ✅ Complete |
| **Navigation Menus** | ~5ms | Menu structure, broken menu links | ✅ Complete |
| **Links** | ~50-100ms | Internal/external link validation | ✅ Complete |

### ✅ Phase 2: Build-Time Checks
| Validator | Speed | What It Checks | Status |
|-----------|-------|----------------|--------|
| **Navigation** | ~20ms | Next/prev chains, breadcrumbs, sections | ✅ Complete |
| **Taxonomies** | ~30ms | Tags, archives, pagination integrity | ✅ Complete |
| **Rendering** | ~50ms | HTML structure, Jinja2, SEO metadata | ✅ Complete |
| **Directives** | ~40ms | Directive syntax, completeness, performance | ✅ Complete |

### ✅ Phase 3: Advanced Checks
| Validator | Speed | What It Checks | Status |
|-----------|-------|----------------|--------|
| **Cache Integrity** | ~10ms | Incremental build cache validity | ✅ Complete |
| **Performance** | ~1ms | Build time, throughput, slow pages | ✅ Complete |

**Total Time**: ~200-250ms for comprehensive checks

---

## Recommended Additions (4)

### ⭐ Phase 4: Production-Ready Checks

| Validator | Speed | What It Checks | Priority | Effort |
|-----------|-------|----------------|----------|--------|
| **RSS Feed** | ~20ms | RSS XML validity, URLs, date formatting | ⭐⭐⭐ High | 2-3h |
| **Sitemap** | ~30ms | Sitemap XML validity, duplicate URLs | ⭐⭐⭐ High | 2-3h |
| **Fonts** | ~10ms | Font downloads, CSS generation, sizes | ⭐⭐⭐ High | 1-2h |
| **Asset Processing** | ~50ms | Asset hashing, minification, optimization | ⭐⭐ Medium | 3-4h |

**New Total Time**: ~300-350ms (still very fast!)

---

## Not Recommended (5)

| Validator | Why Not | Alternative |
|-----------|---------|-------------|
| **Accessibility** | Too complex, slow | Use external tool (axe, lighthouse) |
| **Security** | Static sites are secure | Spot-check templates manually |
| **Theme** | Rendering validator covers it | Let users customize themes |
| **Dev Server** | Issues are obvious | Integration tests better |
| **Search Index** | Optional feature | Wait for user demand |

---

## Coverage Visualization

```
BEFORE (Current):
┌─────────────────────────────────────────┐
│ Core Build Pipeline        ████████████ │ 10/10 ✅
│ Navigation & Structure     ████████████ │ 10/10 ✅
│ Content Quality           ███████████  │ 9/10 ✅
│ Performance              ████████     │ 7/10 ✅
│ Production Features      ████         │ 4/10 ⚠️  ← Gap!
│ Advanced Features        ███          │ 3/10 ⚠️
└─────────────────────────────────────────┘
OVERALL: 8.5/10

AFTER (With Additions):
┌─────────────────────────────────────────┐
│ Core Build Pipeline        ████████████ │ 10/10 ✅
│ Navigation & Structure     ████████████ │ 10/10 ✅
│ Content Quality           ███████████  │ 9/10 ✅
│ Performance              ████████     │ 7/10 ✅
│ Production Features      ███████████  │ 9/10 ✅ ← Fixed!
│ Advanced Features        ████         │ 4/10 📈
└─────────────────────────────────────────┘
OVERALL: 9.5/10
```

---

## Configuration Examples

### Minimal (Use Defaults)
```toml
# bengal.toml - Nothing needed, all validators enabled by default
[health_check]
validate_build = true
```

### Disable Specific Validator
```toml
[health_check.validators]
links = false  # Disable link validation (if too slow)
```

### Disable All Health Checks
```toml
[health_check]
validate_build = false
```

### Custom Thresholds
```toml
[health_check.output]
min_page_size = 500  # Smaller threshold for small pages

[health_check.performance]
max_build_time = 60  # Warn if build takes > 60 seconds
```

---

## Running Health Checks

### During Build
```bash
# Health checks run automatically after build
bengal build

# Disable for this build
bengal build --no-validate

# Show verbose output
bengal build --validate-verbose
```

### Manual Health Check
```bash
# Run health checks on existing build
bengal health-check

# Show all checks (not just problems)
bengal health-check --verbose

# JSON output for CI/CD
bengal health-check --json > health-report.json
```

### In CI/CD
```yaml
# .github/workflows/build.yml
- name: Build site
  run: bengal build

- name: Health check
  run: |
    bengal health-check --json > health-report.json
    # Fail if errors found
    if [ $(jq '.summary.errors' health-report.json) -gt 0 ]; then
      exit 1
    fi
```

---

## Interpreting Results

### Report Format
```
🏥 Health Check Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Configuration         passed
✅ Output                passed
⚠️ Navigation Menus      1 warning(s)
   • Menu 'main' has 1 item(s) with potentially broken links
     💡 Check menu URLs in bengal.toml
        - About → /about/
❌ Links                 3 error(s)
   • 3 broken internal link(s)
     💡 Fix broken internal links. They point to pages that don't exist.
        - /old-page/
        - /moved-page/
        - /deleted-page/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 8 passed, 1 warnings, 3 errors
Build Quality: 72% (Fair)
```

### Status Levels

| Symbol | Level | Meaning | Action |
|--------|-------|---------|--------|
| ✅ | Success | Everything OK | None needed |
| ℹ️ | Info | FYI, not a problem | Optional improvement |
| ⚠️ | Warning | Not critical but should fix | Fix when convenient |
| ❌ | Error | Critical issue | Fix immediately |

### Quality Scores

| Score | Rating | Meaning |
|-------|--------|---------|
| 95-100% | Excellent | Production-ready |
| 85-94% | Good | Minor issues to address |
| 70-84% | Fair | Several issues to fix |
| < 70% | Needs Improvement | Not ready for production |

---

## Writing Custom Validators

### Template
```python
# my_validator.py
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

class MyValidator(BaseValidator):
    name = "My Custom Check"
    description = "Validates something custom"
    enabled_by_default = True
    
    def validate(self, site):
        results = []
        
        # Your validation logic
        if something_wrong:
            results.append(CheckResult.error(
                "Problem found",
                recommendation="How to fix it",
                details=["detail 1", "detail 2"]
            ))
        else:
            results.append(CheckResult.success(
                "Everything OK"
            ))
        
        return results

# Register (in site.build() or manually)
from bengal.health import HealthCheck
health = HealthCheck(site, auto_register=False)
health.register(MyValidator())
report = health.run()
```

---

## Performance Tips

### Keep Validators Fast
- ✅ Sample pages instead of checking all (10-20 pages)
- ✅ Early exit on critical errors
- ✅ Cache results when possible
- ✅ Use simple checks over complex analysis
- ❌ Don't re-process files (read only)
- ❌ Don't make network calls (too slow)
- ❌ Don't parse huge files completely

### Target Timing
- Simple validators: < 10ms
- Moderate validators: < 50ms
- Complex validators: < 100ms
- **Never exceed**: 200ms for any single validator

---

## FAQ

**Q: Can I disable health checks entirely?**  
A: Yes, set `validate_build = false` in `[health_check]` section.

**Q: Why do health checks run even on clean builds?**  
A: Health checks verify the *output* quality, not just the build process. Even clean builds can have issues.

**Q: Can health checks fix issues automatically?**  
A: No, health checks only *detect* issues. You must fix them manually. This is by design to prevent unexpected changes.

**Q: Do health checks slow down builds?**  
A: Minimally. Current validators take ~250ms total. Recommended additions add ~100ms. Total < 400ms is acceptable.

**Q: Can I write custom validators?**  
A: Yes! Subclass `BaseValidator` and implement `validate()`. See template above.

**Q: What if a validator crashes?**  
A: Health check system catches exceptions and reports them as errors. Build continues.

**Q: Are health checks required?**  
A: No, but strongly recommended for production sites. They catch issues before deployment.

---

## Next Steps

1. **Review** current health check output after your next build
2. **Identify** any warnings or errors to fix
3. **Configure** validators to match your needs
4. **Consider** adding custom validators for project-specific checks
5. **Integrate** health checks into CI/CD pipeline

---

## Resources

- **Full Analysis**: `HEALTH_CHECK_COVERAGE_ANALYSIS.md`
- **Executive Brief**: `HEALTH_CHECK_EXPANSION_BRIEF.md`
- **Code**: `bengal/health/`
- **Tests**: `tests/unit/health/`

---

**Status**: ✅ System is mature and production-ready  
**Recommendation**: Add 4 validators for complete production coverage

