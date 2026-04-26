"""
Hybrid Search Module
Combines dense vector search with BM25 lexical search
"""

from typing import List, Dict, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
import time


class HybridSearcher:
    """Hybrid search combining dense and sparse retrieval"""
    
    def __init__(self, embedding_store, alpha: float = 0.7):
        """
        Initialize hybrid searcher
        
        Args:
            embedding_store: EmbeddingStore instance
            alpha: Weight for dense search (1-alpha for BM25)
        """
        self.embedding_store = embedding_store
        self.alpha = alpha
        self.bm25_index = None
        self.corpus_texts = []
        self.corpus_metadata = []
    
    def build_bm25_index(self, chunks: List) -> None:
        """Build BM25 index from document chunks"""
        self.corpus_texts = []
        self.corpus_metadata = []
        
        tokenized_corpus = []
        for chunk in chunks:
            text = chunk.content if hasattr(chunk, 'content') else chunk.get('content', '')
            tokens = text.lower().split()
            tokenized_corpus.append(tokens)
            self.corpus_texts.append(text)
            
            metadata = {
                "chunk_id": chunk.chunk_id if hasattr(chunk, 'chunk_id') else chunk.get('chunk_id'),
                "content": text,
                "doc_id": chunk.doc_id if hasattr(chunk, 'doc_id') else chunk.get('doc_id'),
                "doc_name": chunk.doc_name if hasattr(chunk, 'doc_name') else chunk.get('doc_name'),
                "chunk_idx": chunk.chunk_idx if hasattr(chunk, 'chunk_idx') else chunk.get('chunk_idx'),
            }
            self.corpus_metadata.append(metadata)
        
        self.bm25_index = BM25Okapi(tokenized_corpus)
    
    def search(self, query: str, k: int = 5) -> Dict:
        """
        Perform hybrid search combining dense and BM25 retrieval
        
        Args:
            query: Query string
            k: Number of results to retrieve
            
        Returns:
            Dictionary with hybrid search results
        """
        start_time = time.time()
        
        # Dense vector search
        dense_results, dense_scores = self.embedding_store.retrieve(query, k=k*2)
        
        # BM25 search
        bm25_scores = None
        bm25_results = None
        if self.bm25_index:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25_index.get_scores(tokenized_query)
            
            # Get top-k indices from BM25
            top_indices = np.argsort(bm25_scores)[-k*2:][::-1]
            bm25_results = [self.corpus_metadata[i] for i in top_indices]
            bm25_scores = [bm25_scores[i] for i in top_indices]
            
            # Normalize BM25 scores to [0, 1]
            max_score = max(bm25_scores) if bm25_scores else 1
            bm25_scores = [s / max_score if max_score > 0 else 0 for s in bm25_scores]
        
        # Combine results
        combined_scores = {}
        
        # Add dense search scores
        for result, score in zip(dense_results, dense_scores):
            chunk_id = result["chunk_id"]
            combined_scores[chunk_id] = {
                "dense_score": float(score),
                "bm25_score": 0.0,
                "metadata": result
            }
        
        # Add BM25 scores
        if bm25_results:
            for result, score in zip(bm25_results, bm25_scores):
                chunk_id = result["chunk_id"]
                if chunk_id not in combined_scores:
                    combined_scores[chunk_id] = {
                        "dense_score": 0.0,
                        "bm25_score": float(score),
                        "metadata": result
                    }
                else:
                    combined_scores[chunk_id]["bm25_score"] = float(score)
        
        # Calculate hybrid scores
        hybrid_results = []
        for chunk_id, scores_dict in combined_scores.items():
            hybrid_score = (
                self.alpha * scores_dict["dense_score"] + 
                (1 - self.alpha) * scores_dict["bm25_score"]
            )
            scores_dict["hybrid_score"] = hybrid_score
            hybrid_results.append((chunk_id, scores_dict))
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x[1]["hybrid_score"], reverse=True)
        
        # Format results
        retrieved_docs = []
        for i, (chunk_id, scores_dict) in enumerate(hybrid_results[:k]):
            retrieved_docs.append({
                "rank": i + 1,
                "chunk_id": chunk_id,
                "content": scores_dict["metadata"]["content"],
                "doc_id": scores_dict["metadata"]["doc_id"],
                "doc_name": scores_dict["metadata"]["doc_name"],
                "chunk_idx": scores_dict["metadata"]["chunk_idx"],
                "dense_score": scores_dict["dense_score"],
                "bm25_score": scores_dict["bm25_score"],
                "hybrid_score": scores_dict["hybrid_score"],
            })
        
        latency = (time.time() - start_time) * 1000
        
        return {
            "mode": "hybrid_search",
            "query": query,
            "num_retrieved": len(retrieved_docs),
            "retrieved_docs": retrieved_docs,
            "dense_weight": self.alpha,
            "bm25_weight": 1 - self.alpha,
            "latency_ms": latency,
            "pipeline_stages": ["embedding", "bm25_tokenization", "hybrid_scoring", "ranking"],
        }


if __name__ == "__main__":
    print("Hybrid Searcher initialized")
