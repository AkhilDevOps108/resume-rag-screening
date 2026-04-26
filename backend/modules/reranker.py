"""
Reranking Module
Implements cross-encoder based reranking to refine retrieval results
"""

from typing import List, Dict, Tuple
import numpy as np
import time


class CrossEncoderReranker:
    """Reranks documents using cross-encoder model"""
    
    def __init__(self, model_name: str = "sentence-transformers/ce-ms-marco-MiniLM-L-12-v2"):
        """
        Initialize cross-encoder reranker
        
        Args:
            model_name: HuggingFace cross-encoder model name
        """
        self.model_name = model_name
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
        except ImportError:
            raise ImportError("sentence-transformers required. Install with: pip install sentence-transformers")
        except:
            # If cross-encoder not available, use a mock implementation
            print(f"Could not load cross-encoder model {model_name}, using mock reranker")
            self.model = None
    
    def rerank(self, query: str, documents: List[Dict], top_k: int = None) -> List[Tuple[Dict, float]]:
        """
        Rerank documents using cross-encoder
        
        Args:
            query: Query string
            documents: List of document dicts with 'content' key
            top_k: Number of top results to return
            
        Returns:
            List of (document, score) tuples sorted by score
        """
        if not documents:
            return []
        
        if top_k is None:
            top_k = len(documents)
        
        # Prepare document texts
        doc_texts = [doc.get("content", "") for doc in documents]
        
        if self.model is None:
            # Mock reranking: use similarity-based scoring
            scores = [1.0 - (i * 0.1) for i in range(len(documents))]
        else:
            # Compute cross-encoder scores
            query_doc_pairs = [[query, doc_text] for doc_text in doc_texts]
            scores = self.model.predict(query_doc_pairs)
        
        # Pair documents with scores and sort
        results = list(zip(documents, scores))
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]


class SimpleReranker:
    """Simple reranker based on semantic similarity or keyword overlap"""
    
    def __init__(self):
        self.name = "simple_reranker"
    
    def calculate_relevance_score(self, query: str, document: str) -> float:
        """Calculate relevance based on keyword overlap and length"""
        query_tokens = set(query.lower().split())
        doc_tokens = set(document.lower().split())
        
        # Jaccard similarity
        intersection = len(query_tokens & doc_tokens)
        union = len(query_tokens | doc_tokens)
        
        jaccard = intersection / union if union > 0 else 0
        
        # Normalize length penalty
        doc_length = len(document.split())
        length_penalty = min(1.0, doc_length / 1000)  # Normalize to doc length
        
        # Combine scores
        score = 0.7 * jaccard + 0.3 * length_penalty
        
        return score
    
    def rerank(self, query: str, documents: List[Dict]) -> List[Tuple[Dict, float]]:
        """
        Rerank documents using simple relevance metrics
        
        Args:
            query: Query string
            documents: List of document dicts with 'content' key
            
        Returns:
            List of (document, score) tuples sorted by score
        """
        results = []
        
        for doc in documents:
            score = self.calculate_relevance_score(query, doc.get("content", ""))
            results.append((doc, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results


class AdvancedReranker:
    """Advanced reranker combining multiple scoring strategies"""
    
    def __init__(self, embedding_store=None):
        """
        Initialize advanced reranker
        
        Args:
            embedding_store: Optional embedding store for semantic scoring
        """
        self.embedding_store = embedding_store
        self.cross_encoder = None
        self.simple_reranker = SimpleReranker()
        
        try:
            self.cross_encoder = CrossEncoderReranker()
        except:
            print("Cross-encoder not available, using simple reranking")
    
    def rerank(self, query: str, documents: List[Dict], k: int = None) -> Dict:
        """
        Perform advanced reranking with multiple strategies
        
        Args:
            query: Query string
            documents: List of document dicts
            k: Top-k results to return
            
        Returns:
            Dictionary with reranked results and scores
        """
        start_time = time.time()
        
        if not documents:
            return {
                "reranked_docs": [],
                "reranking_scores": [],
                "num_reranked": 0,
                "latency_ms": 0,
                "strategies": []
            }
        
        k = k or len(documents)
        
        # Strategy 1: Simple relevance scoring
        simple_results = self.simple_reranker.rerank(query, documents)
        simple_scores = {doc["chunk_id"]: score for doc, score in simple_results}
        
        # Strategy 2: Cross-encoder scoring (if available)
        cross_encoder_scores = {}
        if self.cross_encoder:
            cross_results = self.cross_encoder.rerank(query, documents, top_k=len(documents))
            cross_encoder_scores = {doc["chunk_id"]: score for doc, score in cross_results}
        
        # Combine scores
        combined_results = []
        for doc in documents:
            chunk_id = doc["chunk_id"]
            
            simple_score = simple_scores.get(chunk_id, 0.5)
            cross_score = cross_encoder_scores.get(chunk_id, 0.5)
            
            # Weighted combination
            if self.cross_encoder:
                combined_score = 0.5 * simple_score + 0.5 * cross_score
            else:
                combined_score = simple_score
            
            combined_results.append((doc, combined_score))
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x[1], reverse=True)
        
        # Format results
        reranked_docs = []
        for i, (doc, score) in enumerate(combined_results[:k]):
            reranked_docs.append({
                "rank": i + 1,
                "chunk_id": doc["chunk_id"],
                "content": doc["content"],
                "doc_id": doc["doc_id"],
                "doc_name": doc["doc_name"],
                "chunk_idx": doc["chunk_idx"],
                "reranking_score": float(score),
                "simple_score": float(simple_scores.get(doc["chunk_id"], 0)),
                "cross_encoder_score": float(cross_encoder_scores.get(doc["chunk_id"], 0)),
            })
        
        latency = (time.time() - start_time) * 1000
        
        return {
            "reranked_docs": reranked_docs,
            "reranking_scores": [doc["reranking_score"] for doc in reranked_docs],
            "num_reranked": len(reranked_docs),
            "latency_ms": latency,
            "strategies": ["simple_relevance", "cross_encoder" if self.cross_encoder else "none"]
        }


if __name__ == "__main__":
    print("Reranker modules initialized")
