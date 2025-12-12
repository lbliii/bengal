# RFC: Next-Generation Build Paradigms for Python 3.14t

## Status
- **Owner**: AI Assistant
- **Created**: 2024-12-05
- **State**: Thought Experiment / Exploration
- **Confidence**: 60% 🟡 (experimental concepts)

## Executive Summary

Python 3.13+ introduces **free-threaded mode** (`python3.13t`) - experimental builds without the Global Interpreter Lock (GIL). This fundamentally changes what's architecturally possible in Python.

This RFC explores novel build paradigms that leverage:
- **True parallelism** (no GIL)
- **Shared memory** between threads
- **Modern Python features** (pattern matching, type hints, dataclasses)
- **Structured concurrency** (TaskGroups, ExceptionGroups)

**Goal**: Identify a paradigm that could make Bengal the first SSG to fully exploit free-threaded Python.

---

## The Game Changer: Free-Threaded Python

### Before (GIL)
```
Thread 1: [====CPU====]------------[====CPU====]------------
Thread 2: ------------[====CPU====]------------[====CPU====]
          ^-- Only one thread executes Python at a time
```

### After (No GIL)
```
Thread 1: [====CPU====][====CPU====][====CPU====]
Thread 2: [====CPU====][====CPU====][====CPU====]
Thread 3: [====CPU====][====CPU====][====CPU====]
Thread 4: [====CPU====][====CPU====][====CPU====]
          ^-- True parallel execution on all cores
```

**Implications for SSGs**:
- Shared `Site` object accessible from all threads (no serialization)
- Fine-grained parallelism (per-shortcode, not just per-page)
- No multiprocessing overhead (fork, pickle, IPC)
- Mutable shared caches without locks (using atomics)

---

## Paradigm 1: Dataflow Graph with Lazy Materialization

**Inspiration**: Bazel, Buck, Pants (build systems), Dask (data science)

### Concept

Define the build as a **directed acyclic graph (DAG)** of pure computations. The framework:
1. Automatically builds the dependency graph
2. Executes nodes in parallel where dependencies allow
3. Caches results by input hash (content-addressable)
4. Incrementally recomputes only what changed

### Design

```python
from bengal.graph import node, depends_on, Graph

# Define computation nodes as pure functions
@node
def content_hash(page: Page) -> str:
    """Hash of raw content - cache key for downstream."""
    return hashlib.sha256(page.content.encode()).hexdigest()

@node
@depends_on(content_hash)
def parsed_ast(page: Page, content_hash: str) -> AST:
    """Parse markdown to AST. Cached by content_hash."""
    return parse_markdown(page.content)

@node
@depends_on(parsed_ast)
def table_of_contents(page: Page, ast: AST) -> list[TOCEntry]:
    """Extract TOC from AST."""
    return extract_toc(ast)

@node
def all_pages(site: Site) -> list[Page]:
    """Barrier node: collect all discovered pages."""
    return site.pages

@node
@depends_on(all_pages)
def navigation(pages: list[Page]) -> Navigation:
    """Build navigation from all pages."""
    return build_navigation(pages)

@node
@depends_on(parsed_ast, navigation)
def rendered_html(page: Page, ast: AST, nav: Navigation) -> str:
    """Render page with template. Depends on AST and nav."""
    return render_template(page, ast, nav)

# Build execution
graph = Graph()
graph.add_pages(site.pages)
graph.execute(workers=os.cpu_count())  # True parallel with 3.14t
```

### Execution Model

```
                    ┌─────────────────┐
                    │   all_pages     │ (barrier)
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │navigation│  │ page[0]  │  │ page[1]  │ ...
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │             │             │
             │    ┌────────┴────────┐    │
             │    ▼                 ▼    │
             │ content_hash    content_hash
             │    │                 │    │
             │    ▼                 ▼    │
             │ parsed_ast      parsed_ast│
             │    │                 │    │
             │    ▼                 ▼    │
             └──►rendered_html◄────┴────┘
```

### Advantages
- **Automatic parallelism**: Framework determines what can run in parallel
- **Perfect incrementality**: Only recompute nodes whose inputs changed
- **Content-addressable cache**: Results cached by input hash
- **Declarative**: Describe what, not how

### Challenges
- Learning curve for graph-based thinking
- Debugging can be harder (non-linear execution)
- Barrier nodes (navigation, search) limit parallelism

---

## Paradigm 2: Self-Adjusting Computation (SAC)

**Inspiration**: Academic research by Umut Acar, Adapton framework

### Concept

Every computation is **automatically tracked**. When inputs change, the system **propagates changes** through dependent computations, re-running only what's necessary.

### Design

```python
from bengal.sac import memo, ref, Ref

# Refs are reactive values that track dependencies
class Page:
    content: Ref[str]
    metadata: Ref[dict]

    @memo
    def parsed_ast(self) -> AST:
        # Automatically tracks dependency on self.content
        return parse_markdown(self.content.get())

    @memo
    def rendered_html(self, nav: Navigation) -> str:
        # Tracks dependencies on parsed_ast and nav
        ast = self.parsed_ast()
        return render_template(self, ast, nav)

# When content changes, only affected computations re-run
page.content.set("# New Content")  # Triggers re-computation
# parsed_ast() re-runs
# rendered_html() re-runs
# Other pages: unchanged
```

### Execution Model

```python
# Build phase
site = Site.from_config(path)
for page in site.pages:
    page.rendered_html(site.navigation)  # Memoized

# Incremental rebuild
changed_file = "content/blog/post.md"
page = site.get_page(changed_file)
page.content.set(read_file(changed_file))

# SAC automatically:
# 1. Invalidates page.parsed_ast (depends on content)
# 2. Invalidates page.rendered_html (depends on parsed_ast)
# 3. Does NOT invalidate other pages
# 4. Re-runs only invalidated computations
```

### Advantages
- **Minimal recomputation**: Provably optimal incrementality
- **No manual dependency tracking**: Framework handles it
- **Fine-grained**: Tracks dependencies at expression level

### Challenges
- Runtime overhead for dependency tracking
- Memory overhead for memoization
- Complex implementation

---

## Paradigm 3: Entity-Component-System (ECS)

**Inspiration**: Game engines (Unity, Bevy), data-oriented design

### Concept

Separate **data** (components) from **behavior** (systems). Entities are just IDs. Systems iterate over entities with specific component combinations.

### Design

```python
from bengal.ecs import World, Component, System, Query

# Components are pure data
@component
class SourceFile:
    path: Path
    content: str
    mtime: float

@component
class Frontmatter:
    title: str
    date: datetime
    tags: list[str]

@component
class ParsedAST:
    ast: dict
    toc: list[TOCEntry]

@component
class RenderedHTML:
    html: str
    output_path: Path

# Systems process entities with specific components
@system
def parse_system(query: Query[SourceFile, Frontmatter], missing: ParsedAST):
    """Parse all entities that have content but no AST yet."""
    for entity, (source, frontmatter) in query.iter():
        ast = parse_markdown(source.content)
        entity.add(ParsedAST(ast=ast, toc=extract_toc(ast)))

@system
def render_system(query: Query[ParsedAST, Frontmatter], missing: RenderedHTML):
    """Render all entities that have AST but no HTML yet."""
    for entity, (ast, frontmatter) in query.iter():
        html = render_template(frontmatter, ast.ast)
        entity.add(RenderedHTML(html=html, output_path=...))

# Execution
world = World()

# Discovery creates entities with SourceFile + Frontmatter
for path in content_dir.rglob("*.md"):
    entity = world.spawn()
    entity.add(SourceFile(path=path, content=path.read_text(), mtime=path.stat().st_mtime))
    entity.add(Frontmatter(**parse_frontmatter(entity.get(SourceFile).content)))

# Systems run in parallel on entities matching their queries
world.run_systems([parse_system, render_system], parallel=True)
```

### Execution Model

```
World State:
┌─────────┬────────────┬───────────┬──────────┬─────────────┐
│ Entity  │ SourceFile │Frontmatter│ ParsedAST│ RenderedHTML│
├─────────┼────────────┼───────────┼──────────┼─────────────┤
│ page_1  │     ✓      │     ✓     │    ✓     │      ✓      │
│ page_2  │     ✓      │     ✓     │    ✓     │      ✓      │
│ page_3  │     ✓      │     ✓     │    ·     │      ·      │ ← needs parsing
│ asset_1 │     ✓      │     ·     │    ·     │      ·      │ ← not a page
└─────────┴────────────┴───────────┴──────────┴─────────────┘

Systems query for entities matching component patterns:
- parse_system: Has(SourceFile, Frontmatter), Missing(ParsedAST)
- render_system: Has(ParsedAST, Frontmatter), Missing(RenderedHTML)
```

### Advantages
- **Cache-friendly**: Components stored contiguously in memory
- **Parallelism-friendly**: Systems operate on disjoint data
- **Composable**: Add new components/systems without changing existing code
- **Query-based**: Natural expression of "pages that need X"

### Challenges
- Different mental model from OOP
- Component relationships can get complex
- Less natural for hierarchical data (sections, navigation)

---

## Paradigm 4: Structured Concurrency with Task Graphs

**Inspiration**: Python 3.11+ TaskGroups, Trio nurseries, Swift structured concurrency

### Concept

Use **structured concurrency** to express parallel work with clear ownership and cancellation semantics. Tasks form a tree; parent tasks own child tasks.

### Design

```python
from bengal.tasks import TaskGraph, task, barrier

async def build_site(site: Site):
    async with TaskGraph() as graph:
        # Phase 1: Discovery (parallel file reading)
        pages = await graph.map(
            discover_page,
            site.content_dir.rglob("*.md"),
            concurrency=32
        )

        # Barrier: need all pages before navigation
        await graph.barrier()

        # Phase 2: Dependent computations (parallel)
        nav = await graph.run(build_navigation, pages)
        taxonomies = await graph.run(build_taxonomies, pages)

        # Phase 3: Rendering (parallel per page)
        await graph.map(
            render_page,
            pages,
            kwargs={"nav": nav, "taxonomies": taxonomies},
            concurrency=os.cpu_count()
        )

        # Phase 4: Post-processing (parallel)
        await graph.parallel(
            graph.run(generate_sitemap, pages),
            graph.run(generate_rss, pages),
            graph.run(generate_search_index, pages),
        )

# With 3.14t free-threading, this uses real threads
asyncio.run(build_site(site))
```

### Advantages
- **Familiar async/await syntax**: Easy to learn
- **Clear structure**: Task ownership and cancellation
- **Explicit barriers**: Control synchronization points
- **Works today**: Can use with asyncio, enhanced with 3.14t

### Challenges
- Async "colors" everything (async/await propagation)
- Less automatic than SAC or dataflow graphs
- Still requires manual dependency specification

---

## Paradigm 5: Algebraic Effects (Experimental)

**Inspiration**: Koka, Eff, OCaml 5.0

### Concept

Computations can **yield effects** (like "read file", "render template") that are handled by effect handlers. This separates **what** to do from **how** to do it.

### Design

```python
from bengal.effects import effect, handler, perform

# Define effects (what can happen)
@effect
def ReadFile(path: Path) -> str: ...

@effect
def RenderTemplate(template: str, context: dict) -> str: ...

@effect
def WriteFile(path: Path, content: str) -> None: ...

# Pure computation that performs effects
def build_page(page: Page) -> None:
    content = perform(ReadFile(page.source_path))
    ast = parse_markdown(content)
    html = perform(RenderTemplate(page.template, {"page": page, "ast": ast}))
    perform(WriteFile(page.output_path, html))

# Effect handlers (how to handle effects)
@handler(ReadFile)
def cached_read(path: Path) -> str:
    if path in cache:
        return cache[path]
    content = path.read_text()
    cache[path] = content
    return content

@handler(RenderTemplate)
def parallel_render(template: str, context: dict) -> str:
    return jinja_env.get_template(template).render(**context)

# Run with handlers
with handle(cached_read, parallel_render):
    for page in pages:
        build_page(page)  # Effects handled by handlers above
```

### Advantages
- **Pure core logic**: build_page is testable without I/O
- **Swappable handlers**: Easy to mock, cache, parallelize
- **Composable**: Stack handlers for different behaviors

### Challenges
- Very unfamiliar paradigm
- No native Python support (requires library)
- Performance overhead for effect dispatch

---

## Comparison Matrix

| Paradigm | Parallelism | Incrementality | Learning Curve | Python 3.14t Benefit |
|----------|-------------|----------------|----------------|----------------------|
| **Dataflow Graph** | Automatic | Excellent | Medium | High (parallel nodes) |
| **Self-Adjusting** | Manual | Perfect | High | Medium (shared cache) |
| **ECS** | Automatic | Good | Medium | Very High (parallel systems) |
| **Structured Concurrency** | Explicit | Manual | Low | High (real threads) |
| **Algebraic Effects** | Via handlers | Via handlers | Very High | Medium |

---

## Recommendation

### For Bengal's Next Evolution

**Selected Paradigm**: **Dataflow Graph with Lazy Materialization**

This paradigm offers the best balance of automatic parallelism, correctness, and leverage of Python 3.13t+'s free-threaded capabilities. However, adoption requires navigating two critical architectural hurdles:

1.  **The "God Object" Problem**: The current `Site` object is mutable (`self.pages.append(...)`). In a free-threaded environment, mutable shared state requires locking, which negates performance gains.
2.  **Graph Granularity**: A node-per-page graph for a 10k page site creates excessive scheduling overhead.

### Revised Implementation Strategy

We recommend a **Phased Migration** rather than a "Big Bang" rewrite.

#### Phase 1: Coarse-Grained Graph (The "Phased" Approach)
Replace the imperative `BuildOrchestrator` with a graph where nodes represent entire build phases or large batches. This validates the infrastructure without requiring deep changes to `Site`.

- **Nodes**: `Discovery`, `Taxonomy`, `AssetProcessing`, `RenderBatch_A` (pages 1-1000), `RenderBatch_B` (pages 1001-2000).
- **Data Flow**: Nodes still mutate `Site`, but only in disjoint phases or thread-safe batches.
- **Benefit**: Enables parallel asset processing and grouped rendering immediately.

#### Phase 2: Immutable Data Flow (The "Pure" Approach)
Refactor core architecture to separate data definition from execution. Move from `Site` mutation to a functional pipeline:

```python
RawContent -> [DiscoveryNode] -> ContentTree
ContentTree -> [TaxonomyNode] -> EnrichedContent
EnrichedContent -> [RendererNode] -> HTML
```

- **Immutability**: Nodes receive data, compute, and return *new* data structures.
- **Lazy Materialization**: `Site` becomes a read-only facade over the graph results.

### Handling Python < 3.13 (Legacy Support)
The graph executor must support a fallback strategy:
- **Python 3.13t+**: `ThreadPoolExecutor` (True Parallelism)
- **Python < 3.13**: `ProcessPoolExecutor` (Multiprocessing, high overhead) or `ThreadPoolExecutor` (Concurrency, I/O bound only)

### Refined Implementation Sketch

```python
# bengal/next/graph.py
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable
import hashlib
import threading

T = TypeVar('T')

@dataclass
class Node(Generic[T]):
    """A computation node in the build graph."""
    name: str
    compute: Callable[..., T]
    dependencies: list[str]

    def cache_key(self, inputs: dict) -> str:
        """Content-addressable cache key from inputs."""
        return hashlib.sha256(
            str(sorted(inputs.items())).encode()
        ).hexdigest()

class BuildGraph:
    """Dataflow graph with parallel execution."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.cache: dict[str, Any] = {}
        self.results: dict[str, Any] = {}

    def execute(self, target: str, workers: int = None):
        """Execute graph to compute target, using worker threads."""
        workers = workers or os.cpu_count()

        # Build execution plan (topological sort)
        plan = self._topological_sort(target)

        # Execute with thread pool (real parallelism in 3.14t!)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for node_name in plan:
                node = self.nodes[node_name]
                # Wait for dependencies
                dep_results = {d: futures[d].result() for d in node.dependencies}
                # Check cache
                cache_key = node.cache_key(dep_results)
                if cache_key in self.cache:
                    futures[node_name] = pool.submit(lambda: self.cache[cache_key])
                else:
                    # Compute and cache
                    def compute_and_cache(n=node, deps=dep_results, key=cache_key):
                        result = n.compute(**deps)
                        self.cache[key] = result
                        return result
                    futures[node_name] = pool.submit(compute_and_cache)

        return futures[target].result()
```

---

## Next Steps

1. **Prototype dataflow graph** on a branch
2. **Benchmark against current orchestrator** with 3.14t
3. **Measure parallelism gains** on multi-core systems
4. **Evaluate developer experience** (is it intuitive?)
5. **Decide**: Adopt, iterate, or shelve

---

## Open Questions

1. **Is 3.14t stable enough for production?**  
   As of late 2024, it's experimental. Target 3.15/3.16 for stability?

2. **How to handle mutable state (Site object)?**  
   Addressed in Phase 2 via immutable data flow. Intermediate solution uses coarse locking.

3. **Granularity vs. Scheduler Overhead?**  
   Does managing a dependency graph for 10,000+ tiny nodes cost more CPU than we save?
   *Mitigation*: Use batching (coarse-grained nodes) to amortize scheduling costs.

4. **Backward compatibility?**  
   Option A: New API alongside existing orchestrator  
   Option B: Orchestrator becomes a "compatibility layer" over graph

5. **What about Windows/macOS thread performance?**  
   Need benchmarks; thread overhead varies by OS.

---

## References

- [PEP 703: Making the GIL Optional](https://peps.python.org/pep-0703/)
- [Python 3.13 Free-Threaded Mode](https://docs.python.org/3.13/whatsnew/3.13.html#free-threaded-cpython)
- [Bazel: Correct, reproducible, fast builds](https://bazel.build/)
- [Adapton: Self-Adjusting Computation](https://arxiv.org/abs/1503.07792)
- [Entity Component System FAQ](https://github.com/SanderMertens/ecs-faq)
- [Structured Concurrency](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/)
- [Algebraic Effects for the Rest of Us](https://overreacted.io/algebraic-effects-for-the-rest-of-us/)
