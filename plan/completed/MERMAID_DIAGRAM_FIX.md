# Mermaid Diagram Syntax Fix
*Fixed: October 5, 2025*

## Issue

When previewing ARCHITECTURE.md, several Mermaid diagrams showed the error:
```
No diagram type detected matching given configuration for text:
```

## Root Cause

Two diagrams used the `&` operator to combine multiple nodes, which is **not valid Mermaid syntax**:

### Problem 1 (Line 48):
```mermaid
Discovery --> Pages & Sections & Assets
```

### Problem 2 (Line 509):
```mermaid
Page & Site & Config & Functions --> Jinja[Jinja2 Template Engine]
```

The `&` operator doesn't exist in Mermaid - you must use separate arrow declarations.

## Solution

### Fix 1 - Architecture Overview Diagram:
**Before:**
```mermaid
Discovery --> Pages & Sections & Assets
```

**After:**
```mermaid
Discovery --> Pages
Discovery --> Sections
Discovery --> Assets
```

### Fix 2 - Rendering Flow Diagram:
**Before:**
```mermaid
Page & Site & Config & Functions --> Jinja[Jinja2 Template Engine]
```

**After:**
```mermaid
Page --> Jinja[Jinja2 Template Engine]
Site --> Jinja
Config --> Jinja
Functions --> Jinja
```

## Verification

All 6 Mermaid diagrams in ARCHITECTURE.md now use valid syntax:
1. ✅ `graph TB` - Architecture Overview (lines 16-66)
2. ✅ `classDiagram` - Object Model (lines 220-311)
3. ✅ `flowchart TD` - Incremental Build Flow (lines 346-378)
4. ✅ `sequenceDiagram` - Build Pipeline Sequence (lines 419-468)
5. ✅ `flowchart TD` - Rendering Flow Detail (lines 490-524)
6. ✅ `flowchart LR` - Autodoc Pipeline (lines 669-710)

## Status

✅ **Fixed** - All diagrams should now render correctly in Markdown preview tools that support Mermaid.

