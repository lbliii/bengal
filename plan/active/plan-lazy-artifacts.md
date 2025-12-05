# Plan: Lazy-Computed Build Artifacts

**Goal**: Centralize expensive build artifacts (KnowledgeGraph) as lazy properties on BuildContext to eliminate 3-4x redundant computations per build.

## Phase 1: Core Infrastructure
- [ ] **Update BuildContext** (`bengal/utils/build_context.py`)
  - Add `_knowledge_graph` field
  - Add `knowledge_graph` lazy property
  - Implement `_build_knowledge_graph()` method

## Phase 2: Orchestrator Updates
- [ ] **Update PostprocessOrchestrator** (`bengal/orchestration/postprocess.py`)
  - Remove local `_build_graph_data()`
  - Update `_generate_output_formats` to use `build_context.knowledge_graph`
- [ ] **Update StreamingRenderOrchestrator** (`bengal/orchestration/streaming.py`)
  - Accept `build_context` in `process()`
  - Use `build_context.knowledge_graph` instead of building local graph

## Phase 3: Consumer Updates
- [ ] **Update SpecialPagesGenerator** (`bengal/postprocess/special_pages.py`)
  - Add `build_context` param to `generate()` and `_generate_graph()`
  - Use `build_context.knowledge_graph`
- [ ] **Update OutputFormatsGenerator** (`bengal/postprocess/output_formats/__init__.py`)
  - Ensure it receives graph data from context

## Phase 4: Health Check Updates
- [ ] **Update BaseValidator** (`bengal/health/base.py`)
  - Update `validate()` signature to accept optional `build_context`
- [ ] **Update ConnectivityValidator** (`bengal/health/validators/connectivity.py`)
  - Use `build_context.knowledge_graph` if available
  - Keep fallback for standalone usage
- [ ] **Update Health Check Runner** (`bengal/health/health_check.py` & `bengal/orchestration/build/finalization.py`)
  - Pass `build_context` through `run_health_check` to validators

## Verification
- [ ] **Unit Tests**: Verify lazy loading works and caches result
- [ ] **Integration Test**: Verify single graph build across full build lifecycle
- [ ] **Performance**: Measure build time reduction (expect ~400-800ms)
