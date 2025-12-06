# Plan: Lazy-Computed Build Artifacts

**Goal**: Centralize expensive build artifacts (KnowledgeGraph) as lazy properties on BuildContext to eliminate 3-4x redundant computations per build.

**Status**: ✅ **COMPLETE** - All phases implemented

## Phase 1: Core Infrastructure
- [x] **Update BuildContext** (`bengal/utils/build_context.py`)
  - Add `_knowledge_graph` field
  - Add `knowledge_graph` lazy property
  - Implement `_build_knowledge_graph()` method

## Phase 2: Orchestrator Updates
- [x] **Update PostprocessOrchestrator** (`bengal/orchestration/postprocess.py`)
  - Update `_build_graph_data()` to use `build_context.knowledge_graph` property
  - `_generate_output_formats` uses `build_context.knowledge_graph` via `_build_graph_data()`
- [x] **Update StreamingRenderOrchestrator** (`bengal/orchestration/streaming.py`)
  - Accept `build_context` in `process()`
  - Use `build_context.knowledge_graph` instead of building local graph

## Phase 3: Consumer Updates
- [x] **Update SpecialPagesGenerator** (`bengal/postprocess/special_pages.py`)
  - Add `build_context` param to `generate()` and `_generate_graph()`
  - Use `build_context.knowledge_graph`
- [x] **Update OutputFormatsGenerator** (`bengal/postprocess/output_formats/__init__.py`)
  - Receives graph data from context via PostprocessOrchestrator

## Phase 4: Health Check Updates
- [x] **Update BaseValidator** (`bengal/health/base.py`)
  - Update `validate()` signature to accept optional `build_context`
- [x] **Update ConnectivityValidator** (`bengal/health/validators/connectivity.py`)
  - Use `build_context.knowledge_graph` if available
  - Keep fallback for standalone usage
- [x] **Update Health Check Runner** (`bengal/health/health_check.py` & `bengal/orchestration/build/finalization.py`)
  - Pass `build_context` through `run_health_check` to validators

## Verification
- [x] **Unit Tests**: Lazy loading verified in `tests/unit/utils/test_build_context.py`
- [x] **Integration**: Single graph build verified across full build lifecycle
- [x] **Performance**: Build time reduction achieved (eliminates 3-4x redundant graph builds)

## Implementation Notes

- **BuildContext**: Lazy property caches graph on first access, eliminates redundant builds
- **StreamingRenderOrchestrator**: Now uses cached graph from context when available
- **PostprocessOrchestrator**: Uses cached graph via property access
- **SpecialPagesGenerator**: Uses cached graph for graph visualization page
- **Health Validators**: ConnectivityValidator uses cached graph, reducing health check time
- **Fallback Support**: All components maintain fallback for standalone usage (no build_context)
