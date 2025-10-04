# Health Check: Quiet Mode Implementation Plan
**Date:** October 4, 2025  
**Priority:** HIGH (UX improvement)  
**Effort:** Medium (2-3 hours)

## Goal

Replace noisy health check output with signal-focused display:
- **Default:** Only show problems (errors + warnings)
- **Verbose:** Full audit trail (current behavior)
- **CI:** Machine-readable format

## Changes Required

### 1. Add Display Modes to `HealthReport.format_console()`

File: `bengal/health/report.py`

```python
def format_console(self, mode: str = "auto", show_success: bool = False) -> str:
    """
    Format report for console output.
    
    Args:
        mode: Display mode - "auto" (default), "quiet", "normal", "verbose"
        show_success: If True, show successful validators (legacy behavior)
        
    Returns:
        Formatted string ready to print
    """
    # Auto-detect mode based on results
    if mode == "auto":
        if not self.has_problems():
            mode = "quiet"
        else:
            mode = "normal"
    
    if mode == "quiet":
        return self._format_quiet()
    elif mode == "verbose":
        return self._format_verbose()
    else:
        return self._format_normal()


def _format_quiet(self) -> str:
    """Minimal output - perfect builds get one line."""
    lines = []
    
    # Perfect build - just success message
    if not self.has_problems():
        score = self.build_quality_score()
        return f"✓ Build complete. All health checks passed (quality: {score}%)\n"
    
    # Has problems - show them
    lines.append("\n⚠️ Health Check Issues:\n")
    
    # Group by validator, only show problems
    for vr in self.validator_reports:
        if not vr.has_problems:
            continue
        
        # Show validator name if it has problems
        problem_count = vr.warning_count + vr.error_count
        emoji = "❌" if vr.error_count > 0 else "⚠️"
        lines.append(f"{emoji} {vr.validator_name} ({problem_count} issue(s)):")
        
        # Show problem messages
        for result in vr.results:
            if result.is_problem():
                lines.append(f"   • {result.message}")
                
                # Show recommendation
                if result.recommendation:
                    lines.append(f"     💡 {result.recommendation}")
                
                # Show first 3 details
                if result.details:
                    for detail in result.details[:3]:
                        lines.append(f"        - {detail}")
                    if len(result.details) > 3:
                        remaining = len(result.details) - 3
                        lines.append(f"        ... and {remaining} more")
        
        lines.append("")  # Blank line between validators
    
    # Summary
    score = self.build_quality_score()
    rating = self.quality_rating()
    summary = []
    
    if self.total_errors > 0:
        summary.append(f"{self.total_errors} error(s)")
    if self.total_warnings > 0:
        summary.append(f"{self.total_warnings} warning(s)")
    
    lines.append(f"Build Quality: {score}% ({rating}) · {', '.join(summary)}")
    lines.append("💡 Use --health-check=verbose for full report\n")
    
    return "\n".join(lines)


def _format_normal(self) -> str:
    """Balanced output - show summary + problems."""
    lines = []
    
    lines.append("\n🏥 Health Check Summary")
    lines.append("━" * 60)
    lines.append("")
    
    # Show all validators with status
    for vr in self.validator_reports:
        status_line = f"{vr.status_emoji} {vr.validator_name:<20}"
        
        if vr.error_count > 0:
            status_line += f" {vr.error_count} error(s)"
        elif vr.warning_count > 0:
            status_line += f" {vr.warning_count} warning(s)"
        elif vr.info_count > 0:
            status_line += f" {vr.info_count} info"
        else:
            status_line += " passed"
        
        lines.append(status_line)
        
        # Show problems only (not success messages)
        for result in vr.results:
            if result.is_problem():
                lines.append(f"   • {result.message}")
                if result.recommendation:
                    lines.append(f"     💡 {result.recommendation}")
                if result.details:
                    for detail in result.details[:3]:
                        lines.append(f"        - {detail}")
                    if len(result.details) > 3:
                        lines.append(f"        ... and {len(result.details) - 3} more")
    
    # Summary
    lines.append("")
    lines.append("━" * 60)
    lines.append(f"Summary: {self.total_passed} passed, {self.total_warnings} warnings, {self.total_errors} errors")
    
    score = self.build_quality_score()
    rating = self.quality_rating()
    lines.append(f"Build Quality: {score}% ({rating})")
    lines.append("")
    
    return "\n".join(lines)


def _format_verbose(self) -> str:
    """Full audit trail - show everything."""
    # Current implementation
    # (Just rename existing format_console to this)
    pass
```

### 2. Add CLI Flags

File: `bengal/cli.py`

```python
@click.command()
@click.option('--health-check', 
              type=click.Choice(['auto', 'quiet', 'normal', 'verbose', 'off']),
              default='auto',
              help='Health check display mode')
@click.option('--no-health-check', is_flag=True, 
              help='Skip health checks entirely')
def build(health_check, no_health_check, ...):
    """Build the site."""
    
    if no_health_check:
        health_check = 'off'
    
    # Pass mode to health check
    if health_check != 'off':
        report = run_health_checks(site)
        print(report.format_console(mode=health_check))
```

### 3. Update Health Check Invocation

File: `bengal/orchestration/build.py` or wherever health checks are called

```python
def build_site(...):
    # ... build logic ...
    
    # Run health checks with mode from config
    health_mode = config.get('health_check_mode', 'auto')
    report = health_check.run(site)
    
    # Format based on mode
    output = report.format_console(mode=health_mode)
    print(output)
```

### 4. Add Configuration Support

File: `bengal.toml` (user config)

```toml
[health_check]
# Display mode: auto, quiet, normal, verbose, off
mode = "auto"

# CI environment detection
verbose_in_ci = true

# Hide validators that only have successes
hide_passing = true
```

## Example Outputs

### Perfect Build (Quiet Mode)
```
✓ Build complete. All health checks passed (quality: 100%)
```

### Build with Warnings (Quiet Mode)
```
⚠️ Health Check Issues:

⚠️ Directives (3 issue(s)):
   • 8 directive(s) may have fence nesting issues
     💡 Use 4+ backticks (````) for directive fences when content contains 3-backtick code blocks.
        - kitchen-sink.md:159 - tabs
        - kitchen-sink.md:262 - tabs
        - kitchen-sink.md:653 - tabs
        ... and 5 more
   • 22 directive(s) could be improved
     💡 Review directive usage. Consider simpler alternatives for single-item directives.
   • 11 page(s) have heavy directive usage (>10 directives)
     💡 Consider splitting large pages or reducing directive nesting.

⚠️ Navigation Menus (1 issue(s)):
   • Menu 'main' has 4 item(s) with potentially broken links
        - Documentation → /docs/
        - Examples → /examples/
        - Blog → /blog/

Build Quality: 90% (Good) · 5 warning(s)
💡 Use --health-check=verbose for full report
```

### Build with Warnings (Normal Mode)
```
🏥 Health Check Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Configuration        passed
✅ Output               passed
✅ Rendering            passed
⚠️ Directives           3 warning(s)
   • 8 directive(s) may have fence nesting issues
   • 22 directive(s) could be improved
   • 11 page(s) have heavy directive usage (>10 directives)
⚠️ Navigation           1 warning(s)
   • 29 page(s) have invalid breadcrumb trails
⚠️ Navigation Menus     1 warning(s)
   • Menu 'main' has 4 item(s) with potentially broken links
✅ Taxonomies           passed
✅ Links                passed
✅ Cache Integrity      passed
✅ Performance          passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 26 passed, 5 warnings, 0 errors
Build Quality: 90% (Good)
```

### Build with Warnings (Verbose Mode)
```
[Current full output with all details]
```

## Migration Path

### Phase 1: Add Modes (Backward Compatible)
- Add `_format_quiet()` and `_format_normal()`
- Keep existing behavior as default
- Add `--health-check` flag

### Phase 2: Change Default
- Switch default from verbose → auto
- Update documentation
- Announce in changelog

### Phase 3: Deprecation
- Keep verbose available via flag
- Eventually remove old verbose-by-default

## Testing

```python
def test_quiet_mode_perfect_build():
    """Test quiet mode with no issues."""
    report = HealthReport()
    report.validator_reports.append(ValidatorReport(
        validator_name="Test",
        results=[CheckResult.success("All good")]
    ))
    
    output = report.format_console(mode="quiet")
    assert "All health checks passed" in output
    assert "Test" not in output  # Validator name not shown


def test_quiet_mode_with_warnings():
    """Test quiet mode with warnings."""
    report = HealthReport()
    report.validator_reports.append(ValidatorReport(
        validator_name="Test",
        results=[
            CheckResult.success("Good"),
            CheckResult.warning("Bad thing", recommendation="Fix it")
        ]
    ))
    
    output = report.format_console(mode="quiet")
    assert "Bad thing" in output
    assert "Fix it" in output
    assert "Good" not in output  # Success not shown
```

## Rollout Strategy

1. **Week 1:** Implement modes, keep verbose as default
2. **Week 2:** Get user feedback on new modes
3. **Week 3:** Change default to auto
4. **Week 4:** Update all documentation and examples

## Success Metrics

- **Signal-to-noise ratio**: Target 80%+ actionable content
- **User satisfaction**: Survey "health checks are useful"
- **Cognitive load**: Time to parse output < 5 seconds
- **Adoption**: % of users who DON'T disable health checks

---

**Status:** Ready to implement  
**Owner:** TBD  
**Timeline:** 1 week

