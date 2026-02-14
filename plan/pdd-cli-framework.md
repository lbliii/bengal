# Product Design Document: CLI Framework for the b-stack

**Status**: Draft  
**Created**: 2026-02-14  
**Type**: Product Design  
**Scope**: New package (standalone, b-stack integrated)

---

## 1. Executive Summary

A dataclass-first, type-safe CLI framework designed for **build tools, dev servers, and orchestrators**—where parsing, output, and concurrency matter. Built for Python 3.14+ free-threading, with first-class output primitives and ContextVar-based context isolation. Owns the human-interface layer of the b-stack vertical stack, completing full vertical ownership from content to terminal.

**Tagline**: *The CLI framework for tools that do real work.*

---

## 2. Problem Statement

### 2.1 Current Landscape

| Framework | Stars | Approach | Gaps |
|-----------|-------|----------|------|
| Click | ~17k | Decorators, mutable context | No output model, no free-threading, decorator bloat |
| Typer | ~19k | Type hints on Click | Same gaps, still decorator-heavy |
| tyro | ~960 | Dataclass from types | No output, no concurrency story |
| Cappa | ~190 | Dataclass, Clap-inspired | No output, low adoption |

**No framework combines**: dataclass-first parsing + first-class output + free-threading patterns + cancellation + daemon support.

### 2.2 Pain Points (Validated)

1. **Output is an afterthought** — Parsing gets attention; output is ad hoc. Inconsistent spacing, misaligned columns, walls of text. Users "fight it a lot."
2. **Decorator bloat** — 20+ `@click.option` decorators for complex commands. Anti-pattern for type-first, dataclass-driven design.
3. **Mutable context** — `ctx` passed everywhere, implicit state. Doesn't fit free-threading or composition.
4. **No output primitives** — Every project invents sections, tables, spacing. No shared vocabulary.
5. **Impedance mismatch** — CLI produces dict/Namespace; orchestration wants dataclass. Manual mapping required.

### 2.3 b-stack Specific

Bengal (and future Purr, Chirp CLIs) currently:
- Uses Click with custom `BengalCommand`/`BengalGroup` workarounds
- Has `CLIFlags` → `resolve_build_options` → `BuildOptions` flow (correct pattern, but manual)
- Built `CLIOutput` for output—but it's Bengal-specific, not reusable
- Lazy loading, fuzzy matching, aliases—all custom on top of Click

**The human-interface layer is the only b-stack layer we don't own.**

---

## 3. Product Vision

### 3.1 What We're Building

A CLI framework where:

1. **Dataclass is the contract** — Define args as a frozen dataclass; parsing produces it. No decorators. Single source of truth.
2. **Output is first-class** — Sections, tables, key-value, spacing rules. Framework enforces rhythm and hierarchy.
3. **Context is isolated** — ContextVars, not mutable `ctx`. Safe for parallel invocation, daemons, free-threading.
4. **Concurrency is built-in** — Cancellation, parallel I/O, daemon mode. Designed for long-running, I/O-bound tools.
5. **Composition over inheritance** — Protocols, not base classes. Commands are functions; groups are registries.

### 3.2 What We're NOT Building

- A general-purpose replacement for every CLI (simple scripts don't need this)
- A GUI or TUI framework (we integrate with Textual/Rich, don't replace them)
- An async-first framework (sync with free-threading; async can layer on)

---

## 4. Target Users & Use Cases

### 4.1 Primary

| User | Use Case | Why This Framework |
|------|----------|-------------------|
| **Build tool authors** | SSGs, task runners, asset pipelines | Parallel phases, progress, cancellation |
| **Dev server authors** | Hot reload, file watching, daemons | Daemon mode, ContextVars, clean shutdown |
| **Orchestration CLIs** | Multi-repo, bulk operations, sync tools | Parallel I/O, structured output |
| **b-stack maintainers** | Bengal, Purr, Chirp, Kida CLIs | Full vertical ownership, consistent UX |

### 4.2 Secondary

| User | Use Case |
|------|----------|
| **Scriptable tool authors** | `--output json`, piping, CI integration |
| **Plugin-heavy CLIs** | Context isolation, no shared mutable state |
| **Type-first Python teams** | Dataclass args, mypy/pyright compatible |

### 4.3 Out of Scope

- One-off scripts (argparse or tyro sufficient)
- Pure CPU-bound tools (multiprocessing, not threads)
- Simple utilities with 2–3 flags

---

## 5. Core Design Principles

### 5.1 Aligned with b-stack Philosophy

| Principle | Manifestation |
|-----------|---------------|
| **Types as contracts** | Dataclass fields = CLI args; Protocol for commands |
| **Immutable by default** | Frozen dataclass args; no mutation |
| **Composition over inheritance** | No Command/Group base classes; protocols |
| **Explicit boundaries** | CLI → dataclass → orchestration; no implicit ctx |
| **Free-threading ready** | ContextVars, no global mutable state, no GIL assumptions |
| **Single responsibility** | Parsing, output, invocation are separate concerns |

### 5.2 Output Principles

| Principle | Meaning |
|-----------|---------|
| **Rhythm** | Consistent vertical spacing (e.g., blank between sections) |
| **Hierarchy** | Sections, sub-sections, lists—clear visual structure |
| **Alignment** | Tables align; numbers right-aligned |
| **Breathing room** | No walls of text |
| **Progressive disclosure** | Default: concise; verbose: more detail |
| **Graceful degradation** | Works when piped, narrow terminal, non-TTY |

---

## 6. Feature Specification

### 6.1 Parsing Layer

| Feature | Description | Priority |
|---------|-------------|----------|
| **Dataclass-driven args** | Field types + metadata → CLI options. No decorators. | P0 |
| **Subcommands** | Nested commands via `Subcommands[A | B]` or registry | P0 |
| **Help generation** | From docstrings, field metadata | P0 |
| **Config precedence** | CLI > config file > defaults (integrate with resolver pattern) | P1 |
| **Shell completion** | Bash, zsh (at minimum) | P1 |
| **Lazy loading** | Defer command module import until invoked | P1 |
| **Fuzzy matching** | Typo suggestions ("Did you mean...?") | P2 |

### 6.2 Output Layer

| Feature | Description | Priority |
|---------|-------------|----------|
| **Output primitives** | `section()`, `table()`, `key_value()`, `list()`, `blank()` | P0 |
| **Spacing rules** | Configurable rhythm (e.g., blank between sections) | P0 |
| **TTY detection** | Simpler layout when piped/non-TTY | P0 |
| **Structured output** | `--output json | jsonl` for scripting | P0 |
| **Width awareness** | Respect terminal width, wrap when needed | P1 |
| **Progress integration** | Progress bars/spinners that don't corrupt output | P1 |
| **Theme support** | Optional styling (colors, icons); plain fallback | P2 |

### 6.3 Context & Concurrency

| Feature | Description | Priority |
|---------|-------------|----------|
| **ContextVars** | Per-invocation context; no mutable ctx | P0 |
| **Cancellation** | Ctrl+C propagates; clean shutdown | P1 |
| **Daemon mode** | `--daemon` flag; background thread, isolated context | P1 |
| **Parallel I/O** | Optional pool for concurrent operations within command | P2 |

### 6.4 Composition

| Feature | Description | Priority |
|---------|-------------|----------|
| **Command protocol** | `Callable[[Args], None]` or `Callable[[Args], Result]` | P0 |
| **Group registry** | `dict[str, Command]`; no inheritance | P0 |
| **Dependency injection** | Optional: inject resources (config, output) into commands | P2 |

---

## 7. Architecture

### 7.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User                                                            │
│   $ tool build --incremental                                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│ CLI Framework                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Parse     │ argv → BuildArgs (frozen dataclass)                 │
│ Output    │ section(), table(), key_value() — primitives        │
│ Context   │ ContextVar[CLIContext] — per invocation             │
│ Invoke    │ Command protocol → function call                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│ Application (Bengal, Purr, etc.)                               │
│   build(args: BuildArgs) → uses resolve_build_options, etc.    │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Data Flow

```
argv
  → Parser (reads dataclass fields, metadata)
  → BuildArgs (frozen)
  → resolve_*(config, args)  [application-specific]
  → BuildOptions / etc.
  → Orchestration
  → Output primitives (section, table, ...)
  → Terminal
```

### 7.3 Package Structure (Proposed)

```
claw/  # or mew, purr-cli, bengal-cli — TBD
├── parse/       # Dataclass → argparse/options
├── output/      # Primitives, spacing, TTY handling
├── context/     # ContextVar, cancellation
├── invoke/      # Command dispatch, lazy loading
└── __init__.py  # Public API
```

---

## 8. b-stack Integration

### 8.1 Vertical Stack (Updated)

```
┌─────────────────────────────────────────────────────────────────┐
│ Content Layer     │ Patitas, Rosettes                           │
├───────────────────┼─────────────────────────────────────────────┤
│ Rendering Layer   │ Kida                                        │
├───────────────────┼─────────────────────────────────────────────┤
│ Application Layer │ Chirp                                      │
├───────────────────┼─────────────────────────────────────────────┤
│ Transport Layer   │ Pounce                                     │
├───────────────────┼─────────────────────────────────────────────┤
│ Orchestration     │ Bengal, Purr                                │
├───────────────────┼─────────────────────────────────────────────┤
│ Human Interface   │ CLI Framework (this)  ← NEW                │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Migration Path (Bengal)

1. **Phase 1**: Extract `CLIOutput`-style primitives into framework. Bengal uses them.
2. **Phase 2**: Add dataclass parsing for `build` command. Prove BuildArgs flow.
3. **Phase 3**: Migrate remaining commands. Remove Click.
4. **Phase 4**: Purr, Chirp adopt framework for their CLIs.

### 8.3 Shared UX

All b-stack CLIs would share:
- Same output rhythm and hierarchy
- Same argument patterns (dataclass)
- Same help format
- Same error presentation

---

## 9. Competitive Positioning

### 9.1 Positioning Statement

> **"The CLI framework for build tools and dev servers. Dataclass-first. Output as a first-class citizen. Built for Python 3.14+ free-threading."**

### 9.2 Differentiation Matrix

| Dimension | Click/Typer | tyro/Cappa | This Framework |
|-----------|-------------|------------|----------------|
| Parsing | Decorators | Dataclass | Dataclass |
| Output | None | None | First-class primitives |
| Context | Mutable ctx | N/A | ContextVars |
| Free-threading | No | No | Yes |
| Cancellation | No | No | Yes |
| Daemon mode | No | No | Yes |
| Target | General | General | Build tools, orchestrators |

### 9.3 Go-to-Market

1. **Dogfood** — Bengal adopts it. Real-world validation.
2. **Extract** — Standalone package. Clear docs, examples.
3. **Position** — "For tools that do real work." Niche, not general.
4. **Community** — RFC, blog post, PyPI. See who adopts.

---

## 10. Success Metrics

### 10.1 Internal (b-stack)

| Metric | Target |
|--------|--------|
| Bengal migrates off Click | Yes |
| Build command: 20 decorators → 1 dataclass | Yes |
| Purr/Chirp use framework for CLIs | When they have CLIs |
| No regression in CLI startup time | Lazy loading preserved |

### 10.2 External (If Open-Sourced)

| Metric | Target (Year 1) |
|--------|------------------|
| GitHub stars | 100+ |
| PyPI downloads | 1k/month |
| Projects using it (excluding b-stack) | 2+ |
| Issues/PRs from community | Active |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|-------------|
| Scope creep | Strict P0/P1/P2; ship minimal first |
| Maintenance burden | Start as Bengal-internal; extract only if proven |
| Adoption | Don't depend on external adoption for b-stack value |
| Breaking Bengal CLI | Incremental migration; keep Click until full parity |

---

## 12. Roadmap (Tentative)

### Phase 1: Foundation (4–6 weeks)
- [ ] Dataclass parsing (single command)
- [ ] Output primitives (section, table, key_value, blank)
- [ ] ContextVar-based context
- [ ] Command protocol
- [ ] Bengal `build` as proof of concept

### Phase 2: Completeness (4–6 weeks)
- [ ] Subcommands, groups
- [ ] Help generation
- [ ] Shell completion
- [ ] Lazy loading
- [ ] Structured output (--output json)

### Phase 3: Concurrency (2–4 weeks)
- [ ] Cancellation support
- [ ] Daemon mode (optional)
- [ ] TTY vs pipe handling

### Phase 4: Extraction (2–4 weeks)
- [ ] Standalone package
- [ ] Documentation
- [ ] PyPI release (if open-sourcing)

---

## 13. Open Questions

1. **Package name** — claw? mew? bengal-cli? purr-cli? (Avoid confusion with Purr content runtime.)
2. **Rich dependency** — Use Rich for output, or minimal stdlib-only? (Bengal already uses Rich.)
3. **Python version** — 3.14+ only, or 3.12+ with optional 3.14 features?
4. **Open source timing** — With Bengal migration, or after?

---

## 14. References

- `plan/analysis-pipeline-inputs-and-vertical-stacks.md` — Vertical stack philosophy
- `bengal/cli/base.py` — Current BengalCommand, BengalGroup
- `bengal/cli/commands/build.py` — Build command (20+ options)
- `bengal/orchestration/build/options.py` — BuildOptions dataclass
- [Cappa](https://cappa.readthedocs.io/) — Dataclass CLI inspiration
- [tyro](https://brentyi.github.io/tyro/) — Type-driven CLI
- [Please don't use Click](https://xion.io/post/programming/python-dont-use-click.html) — Criticism
