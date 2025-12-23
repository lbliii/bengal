# Bengal Cursor Rules (v3)

New folder-based rule system for Bengal development, inspired by Dori's architecture.

## Structure

```
new-rules/
├── system/                    # Core orchestration rules (alwaysApply)
│   └── bengal-os/RULE.md      # Main command dispatcher
│
├── modules/                   # Shared patterns (alwaysApply: true)
│   ├── types-as-contracts/    # Bengal's core philosophy
│   ├── evidence-handling/     # Code reference patterns
│   ├── architecture-patterns/ # Model/Orchestrator patterns
│   └── output-format/         # Consistent output formatting
│
├── commands/                  # Shortcut command handlers
│   ├── research/              # ::research
│   ├── rfc/                   # ::rfc
│   ├── plan/                  # ::plan
│   ├── implement/             # ::implement
│   ├── validate/              # ::validate
│   └── help/                  # ::? and ::help
│
├── validation/                # Code quality validation
│   ├── type-audit/            # Type system validation with scripts
│   ├── architecture-audit/    # Architecture compliance
│   └── test-coverage/         # Test coverage analysis
│
├── implementation/            # Implementation guides
│   ├── type-first/            # Type-first development
│   ├── add-directive/         # Adding new directives
│   ├── add-filter/            # Adding Jinja filters
│   └── core-model/            # Modifying core models
│
└── workflows/                 # Multi-step workflow chains
    ├── feature/               # ::workflow-feature
    ├── fix/                   # ::workflow-fix
    └── ship/                  # ::workflow-ship
```

## Key Philosophy

Bengal's rules encode its core principles:

1. **Types as Contracts** - Type signatures should be more important than implementations
2. **Models are Passive** - No I/O, no logging, no side effects in `bengal/core/`
3. **Orchestrators Handle Operations** - All build operations in `bengal/orchestration/`
4. **Evidence-First** - All claims require `file:line` code references
5. **Fail Loudly** - Explicit errors over silent degradation

## Migration from Legacy

Convert `.mdc` files to folder format:

```bash
# Legacy: .cursor/rules/validate.mdc
# New:    new-rules/commands/validate/RULE.md
```

Each rule folder can contain:
- `RULE.md` - Main rule definition (required)
- `scripts/` - Co-located validation scripts (optional)
- Other supporting files (schemas, templates)

## Usage

After moving to `.cursor/rules/`:

```yaml
# Shortcuts
::research     # Evidence extraction from codebase
::rfc          # Draft RFC with design options
::plan         # Convert RFC to actionable tasks
::implement    # Guided code changes with guardrails
::validate     # Deep validation with confidence scoring

# Natural language
"How does PageCore work?"           # Routes to ::research
"Add support for custom filters"    # Routes to ::implement
"Check my changes are correct"      # Routes to ::validate
```
