# Output System Alignment Plan

**Status:** Draft  
**Date:** 2025-10-20  
**Context:** Currently have 3 overlapping output systems with different purposes

---

## Current State

### Three Systems

1. **CLIOutput** (`bengal/utils/cli_output.py`)
   - **Purpose:** User-facing CLI messages (commands, interactive prompts, dev server)
   - **Features:** Profile-aware formatting, Rich/fallback, semantic methods
   - **Usage:** `cli.success()`, `cli.error()`, `cli.http_request()`
   - **Scope:** CLI commands, `bengal serve`, user interactions

2. **Structured Logger** (`bengal/utils/logger.py`)
   - **Purpose:** Build-time events, phase tracking, debug/diagnostics
   - **Features:** Phase context, timing, memory tracking, file logging (JSON)
   - **Usage:** `logger.info()`, `logger.warning()`, `with logger.phase()`
   - **Scope:** Build process, internal events, structured logs
   - **Output:** Console (Rich formatted with `●` bullets) + JSON log file

3. **Health Check Reports** (`bengal/health/report.py`)
   - **Purpose:** Build validation and quality reporting
   - **Features:** Multi-format output (console/JSON), quality scoring
   - **Usage:** `report.format_console()`, `report.to_json()`
   - **Scope:** Post-build validation, health diagnostics
   - **Issues:** Uses raw `print()` in orchestration, has own formatting

---

## Problems

### 1. **Inconsistent Output**
- Logger uses `●` bullets with Rich formatting
- CLIOutput uses semantic methods (success, error, warning)
- Health checks use raw `print()` and custom formatting
- No unified styling/theming

### 2. **Duplicate Logic**
- Color/style mapping exists in multiple places
- Rich console detection/usage duplicated
- Status emoji logic scattered (✓, ❌, ⚠️, etc.)

### 3. **Poor Integration**
- Logger and CLIOutput both use Rich but independently
- Health checks don't benefit from CLIOutput's profile awareness
- No consistent quiet/verbose handling across systems

### 4. **Unclear Boundaries**
- When to use `logger.warning()` vs `cli.warning()`?
- Health checks feel like they should use CLIOutput but don't
- Build-time messages mix logger and print statements

---

## Design Principles

### System Purposes (Don't Blur These)

1. **CLIOutput** = User-facing messages
   - Commands success/failure
   - Interactive prompts
   - Progress indicators
   - Dev server output

2. **Logger** = Observability & debugging
   - Build phase tracking
   - Performance metrics
   - Structured events
   - File logging for post-mortem

3. **Health Checks** = Validation reports
   - Post-build quality checks
   - Actionable recommendations
   - Multiple output formats

### Shared Concerns (Need Alignment)

- **Formatting:** Colors, emojis, Rich markup
- **Verbosity:** Profile-aware quiet/verbose modes
- **Console Detection:** TTY, Rich availability
- **User Messages:** Warnings, errors, tips

---

## Proposal: Interface Layer

### Option A: Shared Formatter (Lightweight)

Create a thin formatting layer that all three systems can use:

```python
# bengal/utils/output_formatter.py
class OutputFormatter:
    """Shared formatting utilities for all output systems."""
    
    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Consistent emoji mapping."""
        return {"success": "✓", "error": "❌", "warning": "⚠️"}.get(status, "●")
    
    @staticmethod
    def get_console() -> Console:
        """Singleton Rich console."""
        # Shared instance
    
    @staticmethod
    def should_use_rich() -> bool:
        """Detect Rich availability/TTY."""
        # Unified detection
```

**Pros:** Minimal disruption, reduces duplication  
**Cons:** Doesn't solve integration issues

### Option B: CLIOutput as Foundation (Recommended)

Make CLIOutput the foundation for user-visible messages, keep Logger for internal events:

```python
# bengal/utils/cli_output.py
class CLIOutput:
    # Existing methods...
    
    # New: Health check integration
    def health_result(self, result: CheckResult) -> None:
        """Format health check result."""
        
    def health_summary(self, report: HealthReport) -> None:
        """Format health check summary."""
    
    # New: Logger integration (optional)
    def build_event(self, event: LogEvent) -> None:
        """Format structured log event for console."""
```

**Changes:**
1. Health checks use CLIOutput methods instead of format_console()
2. Logger optionally routes console output through CLIOutput
3. All user-facing output goes through one system

**Pros:** Clear separation, consistent UX, profile-aware  
**Cons:** Requires refactoring health checks

### Option C: Leave Separate (Status Quo)

Keep systems separate but establish clear guidelines:

**Guidelines:**
- **CLIOutput:** Commands, interactive, dev server
- **Logger:** Build events, always log to file, console optional
- **Health Checks:** Own formatting, called explicitly

**Pros:** No breaking changes  
**Cons:** Duplication continues, inconsistent UX

---

## Recommendation

**Go with Option B (CLIOutput as Foundation)**

### Phase 1: Establish Interface ✅ (Done)
- [x] CLIOutput has semantic methods
- [x] Dev server uses CLIOutput
- [x] Clean up noisy warnings

### Phase 2: Health Check Integration
1. Add health-specific methods to CLIOutput:
   - `cli.health_result(CheckResult)`
   - `cli.health_summary(HealthReport)`
   - `cli.validator_status(name, emoji, count)`

2. Update HealthReport:
   - Use CLIOutput in `format_console()`
   - Keep `to_json()` independent
   - Remove raw `print()` from orchestration

3. Update health_check.py:
   - Replace `print()` with CLIOutput calls
   - Use semantic methods (success, warning, error)

### Phase 3: Logger Integration (Optional)
- Keep Logger for structured events
- Optionally route console output through CLIOutput for consistency
- Logger continues JSON file logging independently
- Decision: Do we want build events to use CLI styling?

### Phase 4: Documentation
- Update architecture docs with system boundaries
- Add decision log: When to use which system
- Document the interface contract

---

## Open Questions

1. **Should Logger console output route through CLIOutput?**
   - Pro: Consistent styling
   - Con: Logger is for observability, different audience

2. **Should health checks have direct print() for machine output?**
   - Current: Own formatting
   - Proposed: CLIOutput for console, JSON for machine

3. **Profile awareness in Logger?**
   - Currently: Has verbose flag
   - Should it respect BuildProfile like CLIOutput?

4. **Emoji standardization?**
   - Need consistent mapping across all systems
   - Create central registry?

---

## Decision Needed

Which approach should we take?
- [ ] **Option A:** Shared formatter utilities only
- [ ] **Option B:** CLIOutput as foundation (recommended)
- [ ] **Option C:** Keep separate with guidelines
- [ ] **Custom:** Different approach?

Once decided, we can proceed with implementation.

