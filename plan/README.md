# Bengal Planning & Documentation Directory

This directory contains planning documents, architectural analyses, implementation plans, and post-mortems for the Bengal static site generator project.

## Directory Structure

### `/active/` - Active Work
Plans and designs currently being worked on. These documents represent ongoing efforts that are not yet complete.

**Move here when:** Starting active implementation of a plan.

**Move out when:** Implementation is complete (→ `implemented/`) or work is paused/abandoned (→ `analysis/` or `completed/`).

---

### `/analysis/` - Research & Analysis
Deep dives, investigations, and comparative analyses that inform decision-making but don't necessarily result in immediate implementation.

**Examples:**
- Performance benchmarking results
- Architecture comparisons
- Problem investigations
- Technical research

**Move here when:** Analysis is complete but not yet acted upon.

---

### `/completed/` - Planned (Not Implemented)
Plans and designs that have been drafted, reviewed, and agreed upon, but **not yet implemented**. Think of this as the "ready for implementation" queue.

**Move here when:** 
- Design is finalized and approved
- Implementation details are clear
- Consensus is reached on approach

**Move out when:** Implementation begins (→ `active/`) or is complete (→ `implemented/`).

---

### `/implemented/` - Actually Built
Plans and designs that have been **fully implemented and shipped**. These documents serve as historical records of what was built and why.

**Move here when:**
- Feature/change is fully implemented
- Tests are passing
- Code is merged/deployed

**Naming convention:** Files here often end in `_COMPLETE.md` or `_IMPLEMENTED.md` to clearly indicate completion.

---

### Root `/plan/` - Miscellaneous & Transitional
Documents that don't fit neatly into categories above or are awaiting proper categorization. Try to minimize files here by moving them to appropriate subdirectories.

---

## Workflow

```
┌─────────────┐
│  New Idea   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐      ┌──────────────┐
│   /analysis/    │◄─────┤ Research     │
│ (if needed)     │      └──────────────┘
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  /completed/    │  ◄── "Plan is ready"
│ (plan drafted)  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│    /active/     │  ◄── "Working on it"
│ (implementing)  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ /implemented/   │  ◄── "It's done!"
│  (shipped)      │
└─────────────────┘
```

---

## File Naming Conventions

### Suffixes
- `_ANALYSIS.md` - Deep dive or investigation (usually → `/analysis/`)
- `_PLAN.md` or `_STRATEGY.md` - Design document (→ `/completed/` when ready)
- `_IMPLEMENTATION.md` - Implementation guide (→ `/active/` during work)
- `_COMPLETE.md` or `_IMPLEMENTED.md` - Finished work (→ `/implemented/`)
- `_SUMMARY.md` - Post-mortem or retrospective (→ `/implemented/`)

### Prefixes
Use clear, descriptive names that indicate the feature/area:
- `PERFORMANCE_*` - Performance-related work
- `LIVE_RELOAD_*` - Live reload feature
- `CSS_*` - CSS processing
- `HEALTH_CHECK_*` - Health check system
- etc.

---

## Document Templates

### Analysis Document
```markdown
# [Feature Name] Analysis

## Context
Why are we investigating this?

## Current State
What's the situation now?

## Findings
What did we discover?

## Recommendations
What should we do?

## References
- Links to related docs
- External resources
```

### Implementation Plan
```markdown
# [Feature Name] Implementation Plan

## Goals
What are we trying to achieve?

## Design
How will it work?

## Implementation Steps
1. Step one
2. Step two
...

## Testing Strategy
How will we verify it works?

## Rollout Plan
How will we deploy it?
```

### Completion Summary
```markdown
# [Feature Name] Implementation Complete

## What Was Built
Description of the implementation.

## Key Changes
- Change 1
- Change 2

## Testing
How it was tested.

## Lessons Learned
What went well, what didn't.

## Future Work
Ideas for improvements.
```

---

## Maintenance Guidelines

### For AI Assistants
When instructed to move a completed plan to `/completed/`:
1. **Ask for clarification:** "Is the plan drafted and ready (→ `/completed/`), or is it actually implemented (→ `/implemented/`)?"
2. Move to the appropriate directory
3. Update any references in other documents

### For Developers
- **Review this structure** before creating new planning documents
- **File documents promptly** - don't let files accumulate in the root
- **Keep status current** - move files as work progresses
- **Archive old work** - consider moving very old implemented items to a `archived/` directory if needed

---

## Migration Notes

**✓ Migration Complete (October 9, 2025):** All existing files have been reorganized according to this structure:

- **41 documents** moved to `/implemented/` - completed features and implementations
- **12 documents** moved to `/analysis/` - research, benchmarks, and technical investigations  
- **15 documents** in `/completed/` - plans ready for implementation
- **7 documents** in `/active/` - current work in progress

The `/plan/` root directory now only contains this README. All planning documents have been properly categorized.

---

## Quick Reference

| Status | Directory | Example |
|--------|-----------|---------|
| Just researching | `/analysis/` | `PERFORMANCE_OPTIMIZATION_ANALYSIS.md` |
| Plan is ready | `/completed/` | `KNOWLEDGE_GRAPH_IMPLEMENTATION_PLAN.md` |
| Currently building | `/active/` | `LIVE_RELOAD_IMPLEMENTATION.md` |
| Feature shipped | `/implemented/` | `CSS_BUNDLING_IMPLEMENTATION_COMPLETE.md` |

---

*Last Updated: October 9, 2025*

