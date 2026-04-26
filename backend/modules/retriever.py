"""
Standard RAG Retriever
Implements traditional RAG pipeline with simple cosine similarity retrieval
"""

from typing import List, Dict, Tuple, Optional
import time


class StandardRAGRetriever:
    """Standard RAG retriever using cosine similarity"""
    
    def __init__(self, embedding_store):
        """
        Initialize retriever with embedding store
        
        Args:
            embedding_store: EmbeddingStore instance with vector database
        """
        self.embedding_store = embedding_store
    
    def retrieve(self, query: str, k: int = 5) -> Dict:
        """
        Retrieve top-k chunks using cosine similarity
        
        Args:
            query: Query string
            k: Number of chunks to retrieve
            
        Returns:
            Dictionary with retrieval results and metadata
        """
        start_time = time.time()
        
        # Get top-k results from embedding store (uses cosine similarity)
        results, similarity_scores = self.embedding_store.retrieve(query, k=k)
        
        retrieval_time = time.time() - start_time
        
        # Format results
        retrieved_docs = []
        for i, (result, score) in enumerate(zip(results, similarity_scores)):
            retrieved_docs.append({
                "rank": i + 1,
                "chunk_id": result["chunk_id"],
                "content": result["content"],
                "doc_id": result["doc_id"],
                "doc_name": result["doc_name"],
                "chunk_idx": result["chunk_idx"],
                "cosine_score": float(score),
                "metadata": result["metadata"]
            })
        
        return {
            "mode": "standard_rag",
            "query": query,
            "num_retrieved": len(retrieved_docs),
            "retrieved_docs": retrieved_docs,
            "retrieval_scores": similarity_scores,
            "latency_ms": retrieval_time * 1000,
            "pipeline_stages": ["embedding", "cosine_search"],
            "total_tokens_used": sum(len(doc["content"].split()) for doc in retrieved_docs)
        }
    
    def batch_retrieve(self, queries: List[str], k: int = 5) -> List[Dict]:
        """Retrieve for multiple queries"""
        results = []
        for query in queries:
            results.append(self.retrieve(query, k=k))
        return results
    
    def get_context(self, query: str, k: int = 5, separator: str = "\n\n") -> str:
        """
        Get formatted context string from retrieved chunks
        
        Args:
            query: Query string
            k: Number of chunks to retrieve
            separator: Separator between chunks
            
        Returns:
            Formatted context string for LLM
        """
        retrieval_result = self.retrieve(query, k=k)
        
        context_parts = []
        for i, doc in enumerate(retrieval_result["retrieved_docs"], 1):
            context_parts.append(f"[Doc {i}] {doc['doc_name']} (Similarity: {doc['cosine_score']:.3f})\n{doc['content']}")
        
        return separator.join(context_parts)


if __name__ == "__main__":
    print("Standard RAG Retriever initialized")
