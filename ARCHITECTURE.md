# System Architecture - Advanced Context-Aware RAG

## Overview

This document describes the current architecture of the Advanced Context-Aware RAG application as it exists today: a single advanced retrieval pipeline, a FastAPI backend, and a one-page React workspace with upload on the left and question answering on the right.

## Current System Shape

```text
Frontend (React)
   Left panel  -> DocumentUpload
   Right panel -> QueryInterface + ChatWindow
            |
            v
FastAPI Backend
   /api/upload
   /api/documents
   /api/health
   /api/retrieve
            |
            v
Advanced Retrieval Pipeline
   ingest -> embeddings -> hybrid retrieval -> reranking -> graph traversal -> context optimization -> Gemini answer
```

## Frontend Architecture

### Main layout

The current UI is a single-page, two-column workspace.

- Left column: document upload and indexing status
- Right column: question entry, answer rendering, loading state, and error state

### Active frontend components

- `App.js`
   - orchestrates layout and API calls
   - tracks upload state and current answer
- `DocumentUpload.js`
   - supports both drag-and-drop and click-to-open file picker
   - uploads selected files to `/api/upload`
- `QueryInterface.js`
   - accepts user questions and sends them to the advanced retrieval endpoint
- `ChatWindow.js`
   - renders the final answer and answer metadata

### UI behavior

1. User uploads files from the left panel
2. Files are indexed by the backend
3. User asks a question from the right panel
4. Frontend calls `/api/retrieve?query=...&k=5`
5. Final answer is displayed in the answer card

## Backend Architecture

### Main entry point

`backend/app.py` initializes the runtime and owns the request flow.

Responsibilities:

- load environment variables
- maintain global RAG system state
- handle uploads and retrieval requests
- prepare context for the LLM
- clean model output before returning it to the UI

### Active endpoints

- `POST /api/upload`
   - accepts PDF, TXT, and Markdown files
   - parses and chunks them
   - indexes them into the current retrieval state
- `GET /api/documents`
   - returns document and chunk counts
- `GET /api/health`
   - reports whether the backend is ready
- `GET /api/retrieve`
   - primary advanced retrieval endpoint used by the frontend

There are still some legacy compatibility routes in the codebase, but they are not part of the main product flow.

## Retrieval Pipeline

The current product uses one advanced pipeline only.

### 1. Ingestion

Module: `backend/modules/ingest.py`

- parses PDF, TXT, and Markdown files
- builds `DocumentChunk` objects
- uses overlapping chunking for continuity

### 2. Embeddings

Module: `backend/modules/embeddings.py`

- generates dense vectors for chunks and queries
- stores vectors in FAISS when available
- can fall back to local hashing embeddings in restricted environments

### 3. Hybrid retrieval

Module: `backend/modules/hybrid_search.py`

- dense path: embedding-based retrieval
- sparse path: BM25 keyword retrieval
- weighted score fusion combines both views

### 4. Reranking

Module: `backend/modules/reranker.py`

- rescales retrieved candidates by query-document relevance
- promotes more useful chunks before graph expansion

### 5. Semantic graph traversal

Module: `backend/modules/semantic_graph.py`

- creates relationships between chunks
- adds semantic and structural edges
- explores neighboring chunks for supporting evidence

### 6. Context optimization

Module: `backend/modules/context_optimizer.py`

- removes redundant chunks
- filters weak evidence
- compresses content to reduce token waste

### 7. Answer generation

Module path: `backend/app.py`

- formats the optimized context into a prompt
- sends the context and question to Gemini
- falls back to local synthesis only if Gemini is unavailable or errors out
- applies answer cleanup before returning text to the frontend

## RAGSystem State Model

The backend uses an in-memory `RAGSystem` object to keep the active document and retrieval state.

Tracked state includes:

- parsed chunks
- embedding store
- hybrid searcher
- reranker
- semantic graph
- metrics collector

This keeps the current implementation simple and fast for local usage, but it is still single-process and in-memory.

## Data Flow

### Upload flow

```text
User selects files
-> Frontend sends multipart form data to /api/upload
-> Backend parses files into chunks
-> Chunks are embedded and indexed
-> Retrieval components are rebuilt or updated
-> Frontend refreshes readiness/document counts
```

### Question flow

```text
User asks question
-> Frontend calls /api/retrieve
-> Hybrid retrieval fetches candidate chunks
-> Reranker reorders them
-> Semantic graph expands related evidence
-> Context optimizer compresses final context
-> Gemini receives question + context
-> Answer is cleaned and returned to UI
```

## Current Design Decisions

### Answer-first UX

The current UI intentionally prioritizes the final answer instead of exposing diagnostics, metrics, or comparison panels in the main view.

### Advanced-only product flow

The main application no longer presents standard-vs-advanced switching to the user. The default interaction is a single advanced retrieval path.

### Local-friendly operation

The backend supports fallback embedding behavior so the application can still operate in restricted corporate or SSL-constrained environments.

## Known Constraints

- Retrieval state is kept in memory only
- FAISS index is local to one process
- Graph construction is recomputed in-process
- PDF extraction quality depends on source text quality
- Gemini output quality depends on prompt + source chunk quality

## Suggested Future Improvements

- persist chunk metadata and indexes beyond process memory
- improve PDF cleanup before chunking
- add explicit failure mode when Gemini cannot be reached
- add source citation rendering in the answer card
- add streaming answer output for long responses

## Summary

The current project is an advanced-only context-aware RAG application with:

- one upload-and-query workflow
- one advanced retrieval pipeline
- one answer-first UI
- Gemini-backed final response generation

It is no longer a dual-mode comparison product in its active user experience.
   - Fixed weight = 0.8
   - Maintains document coherence

**Graph Operations**:
- `get_neighbors(chunk_id, hops)`: Multi-hop expansion
- `find_paths()`: Shortest paths between chunks
- `rank_by_centrality()`: PageRank scoring
- `get_subgraph()`: Extract relevant subgraph

**Algorithm Metrics**:
- Centrality = 0.3*in_degree + 0.3*out_degree + 0.4*pagerank
- Helps identify important hub chunks

### 9. Context Optimizer Module (`context_optimizer.py`)

**Purpose**: Compress and optimize context for LLM

**ContextOptimizer Class**:
1. **Relevance Filtering**: Remove low-score chunks
2. **Deduplication**: Detect and remove similar chunks
3. **Compression**: Summarize document to key sentences
4. **Token Counting**: Track compression ratio

**Algorithms**:
- **Deduplication**: Jaccard similarity threshold
- **Compression**: Position bias + length scoring
- **Extraction**: Select top N sentences

**ContextCompressor Class**:
- Extractive summarization
- Token limit awareness
- Truncation strategies

**Output**:
```python
{
    "optimized_docs": [
        {
            "chunk_id": str,
            "content": str,  # compressed
            "original_content": str,
            "compressed": bool,
            ...
        }
    ],
    "optimization_stats": {
        "original_docs": int,
        "optimized_docs": int,
        "original_tokens": int,
        "final_tokens": int,
        "token_reduction": float,  # 0-1
        "compression_ratio": float
    }
}
```

### 10. Prompt Builder Module (`prompt_builder.py`)

**Purpose**: Construct structured prompts for LLM

**Prompt Types**:
1. **Standard RAG**: Simple context + question
2. **Advanced RAG**: Structured with metadata
3. **Evidence Synthesis**: Multi-source synthesis
4. **Comparison**: Compare multiple answers

**Prompt Structure**:
```
System: {system_prompt}

User: {formatted_question_and_context}

Model responds with: {answer}
```

### 11. Metrics Module (`metrics.py`)

**Purpose**: Collect and analyze performance metrics

**MetricsCollector**: Per-query tracking
- Standard RAG metrics
- Advanced RAG metrics
- Statistics computation

**RAGBenchmark**: Cumulative benchmarking
- Multiple queries comparison
- Summary statistics
- Detailed comparison export

**AdvancedRAGMetrics**: Specialized metrics
- Graph exploration metrics
- Reranking effectiveness
- Context compression stats

**Metrics Collected**:
```python
{
    "latency_ms": float,
    "num_retrieved": int,
    "retrieval_scores": [float],
    "pipeline_stages": [str],
    "total_tokens_used": int,
    
    # Advanced-specific
    "graph_nodes_explored": int,
    "reranking_scores": [float],
    "token_reduction_pct": float,
    "compression_ratio": float
}
```

## Data Flow: Standard RAG Query

```
1. User submits query: "What are main topics?"
   ↓
2. StandardRAGRetriever.retrieve(query, k=5)
   ├─ embedding_store.retrieve(query, k=5)
   │  ├─ Embed query → embedding: [384,]
   │  ├─ Search FAISS → distances, indices
   │  ├─ Fetch metadata for results
   │  └─ Return (results, scores)
   │
   ├─ Format results
   └─ Return retrieval_result
   ↓
3. Record metrics
   └─ metrics_collector.record_standard_rag(metrics)
   ↓
4. Return to frontend
   ├─ retrieved_docs: List[Dict]
   ├─ metrics: Dict
   └─ latency_ms: float
   ↓
5. Frontend displays results
```

## Data Flow: Advanced RAG Query

```
1. User submits query: "What are main topics?"
   ↓
2. Hybrid Search
   ├─ Dense: embed + FAISS search
   ├─ Sparse: BM25 tokenize + search
   ├─ Normalize scores
   ├─ Combine: α*dense + (1-α)*bm25
   └─ Return top-k hybrid results
   ↓
3. Reranking
   ├─ Input: hybrid_results + query
   ├─ Compute reranking scores
   │  ├─ Cross-encoder scoring (if available)
   │  └─ Simple relevance scoring
   ├─ Combine strategies
   └─ Return reranked_docs
   ↓
4. Semantic Graph Traversal
   ├─ For each top-3 reranked doc
   ├─ Get semantic neighbors (hops=2)
   ├─ Rank by centrality
   └─ Include relevant neighbors
   ↓
5. Context Optimization
   ├─ Deduplication
   ├─ Relevance filtering
   ├─ Content compression
   └─ Token counting
   ↓
6. Record metrics
   ├─ Latency for each stage
   ├─ Score tracking
   └─ Token reduction stats
   ↓
7. Return to frontend
   ├─ optimized_docs: List[Dict]
   ├─ metrics: Dict with advanced details
   └─ latency_ms: float
   ↓
8. Frontend displays
   ├─ Results with reranking scores
   ├─ Graph metrics
   ├─ Token reduction %
   └─ Pipeline visualization
```

## Design Decisions

### 1. Chunking Strategy
**Decision**: Sliding window with overlap
**Rationale**:
- Preserves context across chunk boundaries
- Adjustable chunk size for different doc types
- Simple and effective

### 2. Embedding Model
**Decision**: Sentence-transformers all-MiniLM-L6-v2
**Rationale**:
- 384 dimensions: balance quality/speed
- Fast inference (~10ms)
- ~200MB download
- Good general-purpose performance
- Easy to swap with alternatives

### 3. Vector Store
**Decision**: FAISS with L2 distance
**Rationale**:
- Fast approximate/exact search
- Scales to millions of chunks
- L2 distance → cosine similarity conversion
- In-memory fallback for small datasets

### 4. Hybrid Search Weight
**Decision**: α=0.7 (70% dense, 30% BM25)
**Rationale**:
- Emphasize semantic relevance (most important)
- Include lexical/keyword matching (precision)
- Configurable for different use cases

### 5. Graph Edge Threshold
**Decision**: 0.5 cosine similarity
**Rationale**:
- Balances connectivity vs. noise
- ~3 neighbors per node average
- Avoids over-connecting similar chunks

### 6. Reranking Strategy
**Decision**: Combined cross-encoder + simple relevance
**Rationale**:
- Cross-encoder captures query-doc interaction
- Simple relevance provides fast fallback
- Fusion combines strengths of both

### 7. Context Compression
**Decision**: Extractive summarization
**Rationale**:
- Fast (no model required)
- Preserves original text
- Configurable compression ratio
- Easy to understand

### 8. Metrics Collection
**Decision**: Per-query + aggregated stats
**Rationale**:
- Detailed insights into each query
- Aggregate trends across queries
- Comparison between modes
- Exportable for analysis

## Scalability Considerations

### Current Limitations
- In-memory chunk metadata (single machine)
- FAISS index on single machine
- Graph constructed in memory
- No distributed search

### Scaling Opportunities
1. **FAISS GPU**: faiss-gpu for 10x speedup
2. **Distributed FAISS**: Partitioned indexes
3. **Database**: Move chunk metadata to PostgreSQL
4. **Caching**: Redis for embedding cache
5. **Async**: Async processing for large batches

## Security Considerations

1. **Document Privacy**: Files stored locally
2. **No External Calls**: All processing local
3. **Rate Limiting**: Can be added via nginx
4. **Input Validation**: Pydantic models
5. **CORS Configuration**: Customizable origins

## Future Enhancements

1. **LLM Integration**: Connect to OpenAI/Anthropic
2. **Streaming Responses**: Real-time answer generation
3. **Query Expansion**: Auto-generate related queries
4. **Query Fusion**: Aggregate results from multiple queries
5. **Recursive Retrieval**: Iterative refinement loop
6. **Multi-modal**: Support for images, tables
7. **Knowledge Graph Integration**: External KGs
8. **Fine-tuned Models**: Domain-specific embeddings

---

**Document Version**: 1.0
**Last Updated**: 2024
**Status**: Production Ready
