# RFC: Semantic Search During Development

**Status**: Draft  
**Created**: 2025-12-08  
**Author**: AI Assistant  
**Confidence**: 70% 🟡

---

## Executive Summary

Add local embedding-based semantic search to Bengal, enabling developers to find content by meaning rather than just keywords. Search for "authentication configuration" and find pages about OAuth, API keys, and security settings—without those exact words appearing.

---

## Problem Statement

### Current State

Bengal has no built-in search during development. Users rely on:
- `grep` / IDE search (exact string matching)
- Browser search on dev server (client-side, basic)
- External tools (Algolia, requires deployment)

**Evidence**:
- `bengal/cli/`: No search command
- `bengal/postprocess/search_index.py`: Generates JSON for client-side search only

### Pain Points

1. **Keyword mismatch**: Searching "auth" doesn't find "authentication" or "login"
2. **Concept blindness**: Can't search for ideas, only strings
3. **Context switching**: Must deploy to use real search (Algolia)
4. **Discovery**: Hard to find related content when writing new docs

### User Impact

Writers spend time hunting for related pages. They miss opportunities to link related content. Duplicate content gets created because authors don't find existing coverage.

---

## Goals & Non-Goals

**Goals**:
- Natural language queries: "How do I configure caching?"
- Concept matching: "auth" finds pages about OAuth, API keys, sessions
- Fast local search: <500ms response time
- Zero external dependencies at runtime
- Integration with dev workflow (CLI + dev server)

**Non-Goals**:
- Replacing production search (Algolia, Typesense)
- Full-text search engine (Elasticsearch)
- Real-time indexing (batch is fine)
- Multi-language support (English first)

---

## Architecture Impact

**Affected Subsystems**:
- **CLI** (`bengal/cli/`): New search command
- **Server** (`bengal/server/`): Search API endpoint
- **Analysis** (`bengal/analysis/`): Embedding generation
- **Cache** (`bengal/cache/`): Vector storage

**New Components**:
- `bengal/search/` - Semantic search engine
- `bengal/search/embeddings.py` - Text embedding generation
- `bengal/search/vector_store.py` - Vector storage and similarity
- `bengal/search/hybrid.py` - Combine semantic + keyword search

---

## Design Options

### Option A: Local Embeddings with sentence-transformers (Recommended)

**Concept**: Use a small, fast embedding model that runs locally.

**Model Selection**:
```python
# Small but effective models (run on CPU)
MODELS = {
    "fast": "all-MiniLM-L6-v2",      # 80MB, 22M params, fastest
    "balanced": "all-mpnet-base-v2",  # 420MB, 110M params, best quality/speed
    "quality": "all-MiniLM-L12-v2",   # 120MB, 33M params, good balance
}
```

**Implementation**:
```python
# bengal/search/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np

class LocalEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.model.encode(text, normalize_embeddings=True)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for multiple texts."""
        return self.model.encode(texts, normalize_embeddings=True, batch_size=32)

    def embed_page(self, page: Page) -> dict[str, np.ndarray]:
        """Generate embeddings for different parts of a page."""
        return {
            "title": self.embed_text(page.title),
            "description": self.embed_text(page.description or ""),
            "content": self.embed_text(page.plain_text[:8000]),  # Truncate
            "combined": self.embed_text(
                f"{page.title}. {page.description or ''}. {page.plain_text[:2000]}"
            ),
        }
```

**Pros**:
- Works offline
- No API costs
- Fast enough for dev (~50ms per query)
- Good quality embeddings

**Cons**:
- Initial model download (~80-400MB)
- Memory usage during indexing
- CPU-bound (no GPU required but slower than cloud)

---

### Option B: API-Based Embeddings (OpenAI, Cohere)

**Concept**: Use cloud embedding APIs for highest quality.

```python
# bengal/search/embeddings_api.py
import openai

class APIEmbedder:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return np.array([e.embedding for e in response.data])
```

**Pros**:
- Best quality embeddings
- No local compute needed
- Latest models automatically

**Cons**:
- Requires API key and internet
- Per-request costs
- Privacy concerns (content sent to API)
- Latency for each request

---

### Option C: Hybrid Local + BM25

**Concept**: Combine semantic search with traditional keyword matching.

```python
# bengal/search/hybrid.py
from rank_bm25 import BM25Okapi

class HybridSearcher:
    def __init__(self, embedder: LocalEmbedder, pages: list[Page]):
        self.embedder = embedder
        self.pages = pages

        # Build BM25 index for keyword search
        tokenized = [self._tokenize(p.plain_text) for p in pages]
        self.bm25 = BM25Okapi(tokenized)

        # Build vector index for semantic search
        self.vectors = embedder.embed_batch([p.plain_text for p in pages])

    def search(
        self,
        query: str,
        k: int = 10,
        semantic_weight: float = 0.7,
    ) -> list[SearchResult]:
        """Combine semantic and keyword search."""

        # Semantic search
        query_vec = self.embedder.embed_text(query)
        semantic_scores = np.dot(self.vectors, query_vec)

        # Keyword search
        keyword_scores = self.bm25.get_scores(self._tokenize(query))

        # Normalize and combine
        semantic_norm = (semantic_scores - semantic_scores.min()) / (semantic_scores.max() - semantic_scores.min() + 1e-6)
        keyword_norm = (keyword_scores - keyword_scores.min()) / (keyword_scores.max() - keyword_scores.min() + 1e-6)

        combined = semantic_weight * semantic_norm + (1 - semantic_weight) * keyword_norm

        # Return top k
        top_indices = np.argsort(combined)[::-1][:k]
        return [
            SearchResult(
                page=self.pages[i],
                score=combined[i],
                semantic_score=semantic_scores[i],
                keyword_score=keyword_scores[i],
            )
            for i in top_indices
        ]
```

**Pros**:
- Best of both worlds
- Handles exact matches AND concepts
- Fallback when semantic fails

**Cons**:
- More complex
- Two indexes to maintain
- Tuning weight parameter

---

## Recommended Approach: Hybrid Local Search

Use **Option C** with **Option A**'s local embeddings:

```
┌─────────────────────────────────────────────────────────────┐
│                    Semantic Search Pipeline                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐                                         │
│   │    Query     │                                         │
│   │ "auth config"│                                         │
│   └──────┬───────┘                                         │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────────┐    ┌──────────────┐                     │
│   │   Embedder   │    │   Tokenizer  │                     │
│   │  (MiniLM)    │    │   (BM25)     │                     │
│   └──────┬───────┘    └──────┬───────┘                     │
│          │                   │                              │
│          ▼                   ▼                              │
│   ┌──────────────┐    ┌──────────────┐                     │
│   │   Vector     │    │   Keyword    │                     │
│   │   Search     │    │   Search     │                     │
│   └──────┬───────┘    └──────┬───────┘                     │
│          │                   │                              │
│          └─────────┬─────────┘                             │
│                    ▼                                        │
│             ┌──────────────┐                               │
│             │    Fusion    │                               │
│             │  (weighted)  │                               │
│             └──────┬───────┘                               │
│                    │                                        │
│                    ▼                                        │
│             ┌──────────────┐                               │
│             │   Results    │                               │
│             │  (ranked)    │                               │
│             └──────────────┘                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## CLI Interface

### Basic Search

```bash
# Search across all content
bengal search "authentication configuration"

# Results:
#
# 🔍 Search: "authentication configuration"
#
# 1. docs/security/oauth.md (0.89)
#    OAuth 2.0 Configuration Guide
#    "Configure OAuth providers for your application..."
#
# 2. docs/api/auth.md (0.84)
#    API Authentication
#    "Set up API keys and manage authentication..."
#
# 3. docs/config/security.md (0.79)
#    Security Configuration
#    "Security settings including session management..."
```

### Advanced Options

```bash
# Search with filters
bengal search "caching" --section docs/api --type reference

# Search with more results
bengal search "deployment" --limit 20

# Search showing similarity breakdown
bengal search "testing" --verbose

# Output format
bengal search "errors" --format json
bengal search "errors" --format paths-only
```

### Interactive Mode

```bash
bengal search --interactive

🔍 Bengal Search (type 'q' to quit)

> authentication setup
  1. docs/security/oauth.md - OAuth 2.0 Configuration
  2. docs/api/auth.md - API Authentication
  3. docs/tutorials/login.md - Building Login Flow

> [1]  # Opens in editor
> q
```

---

## Dev Server Integration

Add search endpoint to dev server:

```python
# bengal/server/api.py
@app.get("/_bengal/search")
async def search(q: str, limit: int = 10):
    results = searcher.search(q, k=limit)
    return {
        "query": q,
        "results": [
            {
                "path": r.page.path,
                "url": r.page.url,
                "title": r.page.title,
                "excerpt": r.excerpt,
                "score": r.score,
            }
            for r in results
        ]
    }
```

Add search UI to dev server chrome:

```html
<!-- Injected in dev mode -->
<div id="bengal-search" class="bengal-dev-search">
    <input type="text" placeholder="Search docs... (⌘K)" />
    <div class="results"></div>
</div>

<script>
// Cmd+K to open search
document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('bengal-search').classList.add('open');
    }
});
</script>
```

---

## Index Storage

```python
# bengal/search/vector_store.py
import numpy as np
from pathlib import Path

class VectorStore:
    """Simple file-based vector storage."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.index_path = cache_dir / "search_index.npz"
        self.metadata_path = cache_dir / "search_metadata.json"

    def save(
        self,
        vectors: np.ndarray,
        metadata: list[dict],
        model_name: str,
    ):
        """Save index to disk."""
        np.savez_compressed(
            self.index_path,
            vectors=vectors,
            model=model_name,
        )
        self.metadata_path.write_text(json.dumps(metadata))

    def load(self) -> tuple[np.ndarray, list[dict]]:
        """Load index from disk."""
        data = np.load(self.index_path)
        metadata = json.loads(self.metadata_path.read_text())
        return data["vectors"], metadata

    def needs_rebuild(self, pages: list[Page]) -> bool:
        """Check if index needs rebuilding."""
        if not self.index_path.exists():
            return True

        # Check if any page is newer than index
        index_mtime = self.index_path.stat().st_mtime
        for page in pages:
            if page.source_path.stat().st_mtime > index_mtime:
                return True

        return False
```

---

## Configuration

```toml
# bengal.toml
[search]
# Enable semantic search
enabled = true

# Embedding model
model = "all-MiniLM-L6-v2"  # or "all-mpnet-base-v2" for better quality

# Hybrid search weights
semantic_weight = 0.7
keyword_weight = 0.3

# Index settings
index_path = ".bengal/search_index"
auto_rebuild = true

# Optional: API-based embeddings
# [search.api]
# provider = "openai"
# model = "text-embedding-3-small"
# api_key_env = "OPENAI_API_KEY"
```

---

## Implementation Plan

### Phase 1: Core Search (2 weeks)
- [ ] Local embedding with sentence-transformers
- [ ] Vector storage and retrieval
- [ ] Basic CLI search command

### Phase 2: Hybrid Search (1 week)
- [ ] BM25 keyword search
- [ ] Score fusion
- [ ] Relevance tuning

### Phase 3: Integration (2 weeks)
- [ ] Dev server search endpoint
- [ ] Search UI in dev chrome
- [ ] Interactive CLI mode

### Phase 4: Polish (1 week)
- [ ] Incremental index updates
- [ ] API embedding support (optional)
- [ ] Performance optimization

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Index build (1000 pages) | <60s |
| Query latency | <200ms |
| Memory usage (index loaded) | <500MB |
| Model download (first run) | <100MB |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Model download on first run | Medium | High | Clear progress indicator, smaller default model |
| Memory usage for large sites | Medium | Medium | Streaming embeddings, memory-mapped index |
| Embedding quality varies | Medium | Medium | Hybrid search provides fallback |
| Dependency size | Low | Medium | Optional install (`pip install bengal[search]`) |

---

## Dependencies

```toml
# Optional dependencies for search
[project.optional-dependencies]
search = [
    "sentence-transformers>=2.2.0",
    "numpy>=1.24.0",
    "rank-bm25>=0.2.2",
]
```

---

## Open Questions

1. **Should search be opt-in or opt-out?**
   - Proposal: Opt-in via `pip install bengal[search]`

2. **How to handle very large sites (10k+ pages)?**
   - Consider approximate nearest neighbor (FAISS, Annoy)

3. **Multi-language support?**
   - Future: Use multilingual models like `paraphrase-multilingual-MiniLM-L12-v2`

4. **Should we support custom embedding models?**
   - Proposal: Yes, via config

---

## Success Criteria

- [ ] `bengal search "concept"` returns semantically relevant results
- [ ] Query latency <200ms after index built
- [ ] Hybrid search outperforms keyword-only in relevance tests
- [ ] Zero external API calls required for basic usage
- [ ] Dev server search feels instant

---

## References

- [sentence-transformers](https://www.sbert.net/)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Hybrid Search Patterns](https://www.pinecone.io/learn/hybrid-search-intro/)
- [Algolia DocSearch](https://docsearch.algolia.com/)
