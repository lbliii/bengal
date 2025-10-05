# Persona-Based Observability - Visual Architecture

**Visual diagrams showing how the profile system works.**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                          │
│                         bengal build                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Profile Determination                         │
│                                                                  │
│  Priority (highest to lowest):                                  │
│  1. Explicit flags: --dev, --theme-dev                          │
│  2. Legacy flags:   --debug, --verbose                          │
│  3. Config file:    [build] profile = "..."                     │
│  4. Default:        "writer"                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐          ┌───────▼──────┐          ┌──────▼──────┐
    │ WRITER  │          │  THEME DEV   │          │ BENGAL DEV  │
    │ Profile │          │   Profile    │          │   Profile   │
    └────┬────┘          └───────┬──────┘          └──────┬──────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
    ┌─────────────────────────────────────────────────────────────┐
    │            Profile Configuration (get_config)                │
    │                                                              │
    │  • show_phase_timing                                        │
    │  • track_memory                                             │
    │  • enable_debug_output                                      │
    │  • collect_metrics                                          │
    │  • health_checks (enabled/disabled lists)                   │
    │  • verbose_build_stats                                      │
    └────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                  Build Orchestrator                          │
    │                                                              │
    │  Applies profile config to:                                 │
    │  • Logger configuration                                     │
    │  • Performance collector                                    │
    │  • Health check filter                                      │
    │  • Debug output flags                                       │
    │  • Build stats display                                      │
    └────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    Build Execution                           │
    │                                                              │
    │  22 Build Phases → Conditional Feature Execution            │
    └────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────┴───────────────┐
         │                               │
    ┌────▼──────┐              ┌─────────▼────────┐
    │  Console  │              │  Metrics Files   │
    │  Output   │              │  (if enabled)    │
    └───────────┘              └──────────────────┘
```

---

## Profile Configuration Flow

```
                                    WRITER PROFILE
                                    ═══════════════
                                    
┌──────────────┐              ┌─────────────────────────┐
│ bengal build │─────────────▶│ ProfileConfig           │
└──────────────┘              │ ─────────────           │
                              │ show_phase_timing: ❌   │
                              │ track_memory: ❌        │
                              │ debug_output: ❌        │
                              │ collect_metrics: ❌     │
                              │ health_checks: 3/10     │
                              └────────┬────────────────┘
                                       │
                              ┌────────▼────────────────┐
                              │ Features Enabled:       │
                              │ • Basic status          │
                              │ • Link validation       │
                              │ • Error reporting       │
                              └─────────────────────────┘
                              
                              Result: Fast, clean output
                              Build time: 4.7s (-12%)


                                   THEME-DEV PROFILE
                                   ══════════════════
                                   
┌──────────────────────┐    ┌─────────────────────────┐
│ bengal build         │───▶│ ProfileConfig           │
│   --theme-dev        │    │ ─────────────           │
└──────────────────────┘    │ show_phase_timing: ✅   │
                            │ track_memory: ❌        │
                            │ debug_output: ❌        │
                            │ collect_metrics: ⚠️     │
                            │ health_checks: 7/10     │
                            └────────┬────────────────┘
                                     │
                            ┌────────▼────────────────┐
                            │ Features Enabled:       │
                            │ • Phase timing          │
                            │ • Template validation   │
                            │ • Asset tracking        │
                            │ • Navigation checks     │
                            │ • Directive validation  │
                            └─────────────────────────┘
                            
                            Result: Template-focused
                            Build time: 5.1s (-5%)


                                    DEV PROFILE
                                    ════════════
                                    
┌──────────────────────┐    ┌─────────────────────────┐
│ bengal build         │───▶│ ProfileConfig           │
│   --dev              │    │ ─────────────           │
└──────────────────────┘    │ show_phase_timing: ✅   │
                            │ track_memory: ✅        │
                            │ debug_output: ✅        │
                            │ collect_metrics: ✅     │
                            │ health_checks: 10/10    │
                            └────────┬────────────────┘
                                     │
                            ┌────────▼────────────────┐
                            │ Features Enabled:       │
                            │ • Everything            │
                            │ • Memory profiling      │
                            │ • Debug messages        │
                            │ • All health checks     │
                            │ • Metrics collection    │
                            └─────────────────────────┘
                            
                            Result: Full observability
                            Build time: 5.37s (baseline)
```

---

## Feature Gating Architecture

```
                        ┌──────────────────────────┐
                        │   BuildOrchestrator      │
                        │   (has: profile)         │
                        └────────┬─────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
    ┌───────────────────┐  ┌──────────────┐  ┌─────────────────┐
    │ Performance       │  │ Logger       │  │ Health Check    │
    │ Collector         │  │              │  │                 │
    └─────┬─────────────┘  └──┬───────────┘  └────┬────────────┘
          │                   │                   │
          │  if profile       │  if profile       │  if profile
          │  .collect         │  .track           │  .health_checks
          │  _metrics         │  _memory          │  [validator]
          │                   │                   │
          ▼                   ▼                   ▼
    ┌───────────────────┐  ┌──────────────┐  ┌─────────────────┐
    │ ENABLED:          │  │ ENABLED:     │  │ ENABLED:        │
    │ • Dev: ✅         │  │ • Dev: ✅    │  │ • Writer: 3     │
    │ • Theme: ⚠️       │  │ • Theme: ❌  │  │ • Theme: 7      │
    │ • Writer: ❌      │  │ • Writer: ❌ │  │ • Dev: 10       │
    └───────────────────┘  └──────────────┘  └─────────────────┘
```

---

## Health Check Filtering

```
┌─────────────────────────────────────────────────────────────────┐
│                    All 10 Health Validators                      │
│                                                                  │
│  1. Config    2. Output    3. Rendering   4. Directives         │
│  5. Navigation   6. Menu   7. Taxonomy    8. Links              │
│  9. Cache    10. Performance                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Profile Filter
                     ▼
         ┌───────────┴───────────┬──────────────────┐
         │                       │                  │
    ┌────▼────┐          ┌───────▼──────┐   ┌──────▼──────┐
    │ WRITER  │          │  THEME DEV   │   │ BENGAL DEV  │
    └────┬────┘          └───────┬──────┘   └──────┬──────┘
         │                       │                  │
         │                       │                  │
         ▼                       ▼                  ▼
    ┌─────────┐          ┌──────────────┐   ┌─────────────┐
    │ Runs 3: │          │ Runs 7:      │   │ Runs 10:    │
    │         │          │              │   │             │
    │ • Config│          │ • Config     │   │ • All       │
    │ • Output│          │ • Output     │   │   validators│
    │ • Links │          │ • Rendering  │   │             │
    │         │          │ • Directives │   │             │
    │         │          │ • Navigation │   │             │
    │         │          │ • Menu       │   │             │
    │         │          │ • Links      │   │             │
    └─────────┘          └──────────────┘   └─────────────┘
    
    ~50ms                ~300ms               ~650ms
```

---

## Debug Output Control

```
┌──────────────────────────────────────────────────────────────┐
│              Debug Output Sources                            │
│                                                              │
│  • APIDocEnhancer: Badge replacements                       │
│  • Pipeline: Enhancement details                            │
│  • Renderer: Template processing                            │
│  • Parser: Content processing                               │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ Check: should_show_debug()
                       │        (from profile)
                       ▼
         ┌─────────────┴────────────┐
         │                          │
    ┌────▼────┐               ┌─────▼──────┐
    │ Writer  │               │ Bengal Dev │
    │ Theme   │               │            │
    └────┬────┘               └─────┬──────┘
         │                          │
         ▼                          ▼
    ┌─────────┐               ┌─────────────┐
    │ SKIP    │               │ PRINT       │
    │ (quiet) │               │ to stderr   │
    └─────────┘               └─────────────┘
```

---

## Memory Tracking Flow

```
                        ┌───────────────────────┐
                        │  tracemalloc.start()  │
                        └──────────┬────────────┘
                                   │
                        ┌──────────▼────────────┐
                        │ Profile Check:        │
                        │ .track_memory?        │
                        └──────────┬────────────┘
                                   │
                   ┌───────────────┼────────────────┐
                   │               │                │
              ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
              │ WRITER  │    │ THEME DEV │   │ BENGAL DEV│
              └────┬────┘    └─────┬─────┘   └─────┬─────┘
                   │               │               │
                   ▼               ▼               ▼
              ┌─────────┐    ┌──────────┐   ┌──────────────┐
              │ SKIP    │    │ SKIP     │   │ TRACK        │
              │         │    │          │   │              │
              │ -150ms  │    │ -150ms   │   │ • Per phase  │
              │ saved   │    │ saved    │   │ • RSS        │
              └─────────┘    └──────────┘   │ • Heap       │
                                            │ • Peak       │
                                            └──────────────┘
```

---

## Performance Metrics Collection

```
┌─────────────────────────────────────────────────────────────────┐
│                     Build Execution                              │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │Discovery │──▶│Rendering │──▶│  Assets  │──▶│Postproc  │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │ Should Collect?     │
                   │ (profile config)    │
                   └──────────┬──────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
         ┌────▼────┐    ┌─────▼─────┐   ┌─────▼─────┐
         │ WRITER  │    │ THEME DEV │   │ BENGAL DEV│
         └────┬────┘    └─────┬─────┘   └─────┬─────┘
              │               │               │
              ▼               ▼               ▼
         ┌─────────┐    ┌──────────┐   ┌──────────────────┐
         │ SKIP    │    │ BASIC    │   │ FULL             │
         │         │    │          │   │                  │
         │ No      │    │ • Timing │   │ • Timing         │
         │ files   │    │ • Phases │   │ • Memory         │
         │         │    │          │   │ • All metrics    │
         │         │    │ (No mem) │   │                  │
         │         │    │          │   │ Saves to:        │
         │         │    │          │   │ .bengal-metrics/ │
         └─────────┘    └──────────┘   └──────────────────┘
```

---

## Output Display Selection

```
┌─────────────────────────────────────────────────────────────────┐
│                    Build Complete                                │
│                    (stats collected)                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │ Display Function Select │
        │ (based on profile)      │
        └────────────┬────────────┘
                     │
         ┌───────────┴───────────┬──────────────────┐
         │                       │                  │
    ┌────▼────┐          ┌───────▼──────┐   ┌──────▼──────┐
    │ WRITER  │          │  THEME DEV   │   │ BENGAL DEV  │
    └────┬────┘          └───────┬──────┘   └──────┬──────┘
         │                       │                  │
         ▼                       ▼                  ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────┐
│ display_simple   │  │ display_build_stats│  │ display_build_stats│
│ _build_stats()   │  │ (standard)         │  │ (verbose)        │
│                  │  │                    │  │                  │
│ • Status         │  │ • Status           │  │ • Status         │
│ • Errors         │  │ • Phase timing     │  │ • Phase timing   │
│ • Output path    │  │ • Health checks    │  │ • Memory         │
│                  │  │ • Warnings         │  │ • All checks     │
│ (~6 lines)       │  │ • Output path      │  │ • Debug info     │
│                  │  │                    │  │ • Metrics path   │
│                  │  │ (~30-50 lines)     │  │ (~200-230 lines) │
└──────────────────┘  └────────────────────┘  └──────────────────┘
```

---

## CLI Flag Precedence

```
Command Line Flags
─────────────────────────────────────────────────
    │
    ▼
┌────────────────────────────────────────────┐
│ 1. Explicit Profile Flags (Highest)       │
│    --dev, --theme-dev                      │
└────────┬───────────────────────────────────┘
         │ if not present
         ▼
┌────────────────────────────────────────────┐
│ 2. Legacy Flags                            │
│    --debug → dev                           │
│    --verbose → theme-dev                   │
└────────┬───────────────────────────────────┘
         │ if not present
         ▼
┌────────────────────────────────────────────┐
│ 3. Config File                             │
│    [build] profile = "..."                 │
└────────┬───────────────────────────────────┘
         │ if not present
         ▼
┌────────────────────────────────────────────┐
│ 4. Default Profile (Lowest)                │
│    writer                                  │
└────────────────────────────────────────────┘

Example:
─────────
bengal build --dev              → dev (flag wins)

bengal build --verbose          → theme-dev (legacy flag)
  + config: profile = "writer"

bengal build                    → writer (config)
  + config: profile = "theme-dev"

bengal build                    → writer (default)
  + no config
```

---

## Performance Impact Visualization

```
Build Time Comparison (192 pages)
══════════════════════════════════

Current (all features on)
├─────────────────────────────────────────────┤ 5.37s
│                                             │
│ ██████████████████████████████████████████  │
└─────────────────────────────────────────────┘


Writer Profile (minimal features)
├──────────────────────────────────────┤ 4.7s (-12%)
│                                      │
│ ████████████████████████████████████ │
└──────────────────────────────────────┘
           ▲
           └─ 660ms saved


Theme Dev Profile (focused features)
├─────────────────────────────────────────┤ 5.1s (-5%)
│                                         │
│ ██████████████████████████████████████  │
└─────────────────────────────────────────┘
       ▲
       └─ 270ms saved


Bengal Dev Profile (all features)
├─────────────────────────────────────────────┤ 5.37s (same)
│                                             │
│ ██████████████████████████████████████████  │
└─────────────────────────────────────────────┘


Overhead Breakdown:
───────────────────
Memory Tracking:     ████████ 150ms
Health Checks (7):   █████████████████ 400ms
Metrics Collection:  ██ 50ms
Debug Output:        █ 10ms
                     ─────────────────
Total Savings:       ██████████████████████ 660ms (writer)
```

---

## Decision Flow for Users

```
┌──────────────────────────────────────────────────────────┐
│ What are you doing?                                      │
└────────────────────────────┬─────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
          ┌─────▼─────┐ ┌────▼─────┐ ┌───▼──────┐
          │ Writing   │ │ Building │ │ Working  │
          │ content?  │ │ themes?  │ │ on SSG?  │
          └─────┬─────┘ └────┬─────┘ └───┬──────┘
                │            │            │
                │ Yes        │ Yes        │ Yes
                ▼            ▼            ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │ bengal   │ │ bengal   │ │ bengal   │
          │ build    │ │ build    │ │ build    │
          │          │ │ --theme- │ │ --dev    │
          │          │ │   dev    │ │          │
          └────┬─────┘ └────┬─────┘ └────┬─────┘
               │            │            │
               │            │            │
               ▼            ▼            ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │ Writer   │ │ Theme Dev│ │ Dev      │
          │ Profile  │ │ Profile  │ │ Profile  │
          │          │ │          │ │          │
          │ • Fast   │ │ • Focused│ │ • Full   │
          │ • Clean  │ │ • Detail │ │ • Debug  │
          │ • Simple │ │ • Themes │ │ • All    │
          └──────────┘ └──────────┘ └──────────┘
```

---

## System Components Map

```
┌──────────────────────────────────────────────────────────────────┐
│                        Bengal SSG                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  NEW COMPONENTS                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │ bengal/utils/profile.py                            │         │
│  │ ─────────────────────                              │         │
│  │ • BuildProfile enum                                │         │
│  │ • from_string() parser                             │         │
│  │ • get_config() for each profile                    │         │
│  │ • should_show_debug() helper                       │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  MODIFIED COMPONENTS                                             │
│  ┌────────────────────────────────────────────────────┐         │
│  │ bengal/cli.py                                      │         │
│  │ • Add --profile, --theme-dev, --dev flags          │         │
│  │ • Profile determination logic                      │         │
│  │ • Pass profile to build()                          │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │ bengal/orchestration/build.py                      │         │
│  │ • Accept profile parameter                         │         │
│  │ • Conditional feature initialization               │         │
│  │ • Apply profile config                             │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │ bengal/health/health_check.py                      │         │
│  │ • Filter validators by profile                     │         │
│  │ • Pass profile to run()                            │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │ bengal/rendering/* (api_doc_enhancer, pipeline)    │         │
│  │ • Check should_show_debug() before printing        │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
│  ┌────────────────────────────────────────────────────┐         │
│  │ bengal/utils/build_stats.py                        │         │
│  │ • Add display_simple_build_stats()                 │         │
│  │ • Profile-aware display selection                  │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Summary

These diagrams show:
1. **System Architecture**: How profiles flow through the system
2. **Configuration Flow**: How each profile configures features
3. **Feature Gating**: How features are conditionally enabled
4. **Health Check Filtering**: How validators are selected
5. **Performance**: Visual impact of each profile
6. **Decision Tree**: How users choose the right profile

**Key Insight**: Profile system is a thin coordination layer that configures existing features, not a complete rewrite.

**Implementation Complexity**: Low - mostly configuration and filtering logic.

