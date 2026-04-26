"""
Context Optimizer Module
Optimizes and compresses retrieved context before LLM generation
"""

from typing import List, Dict, Tuple
import time
import re


class ContextOptimizer:
    """Optimizes retrieved context for LLM consumption"""
    
    def __init__(self):
        self.compression_threshold = 0.1  # Min relevance score to keep

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9+/.-]+", (text or "").lower())
    
    def remove_redundancy(self, documents: List[Dict], similarity_threshold: float = 0.8) -> List[Dict]:
        """
        Remove redundant documents based on content similarity
        
        Args:
            documents: List of retrieved documents
            similarity_threshold: Minimum similarity to consider redundant
            
        Returns:
            Deduplicated list of documents
        """
        if not documents:
            return []
        
        kept_docs = []
        for i, doc1 in enumerate(documents):
            is_redundant = False
            
            content1 = doc1.get("content", "").lower()
            tokens1 = set(content1.split())
            
            for doc2 in kept_docs:
                content2 = doc2.get("content", "").lower()
                tokens2 = set(content2.split())
                
                # Jaccard similarity
                intersection = len(tokens1 & tokens2)
                union = len(tokens1 | tokens2)
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= similarity_threshold:
                    is_redundant = True
                    break
            
            if not is_redundant:
                kept_docs.append(doc1)
        
        return kept_docs
    
    def filter_by_relevance(self, documents: List[Dict], min_score: float = 0.3) -> List[Dict]:
        """
        Filter documents by relevance score threshold
        
        Args:
            documents: List of documents with relevance scores
            min_score: Minimum relevance score
            
        Returns:
            Filtered list of documents
        """
        filtered = []
        for doc in documents:
            # Look for various score fields
            score = doc.get("reranking_score") or doc.get("hybrid_score") or doc.get("cosine_score") or 0.5
            
            if score >= min_score:
                filtered.append(doc)
        
        return filtered
    
    def compress_document(self, document: Dict, query: str = "", max_sentences: int = 4) -> str:
        """
        Compress a document to key sentences
        
        Args:
            document: Document dict with 'content' key
            max_sentences: Maximum sentences to keep
            
        Returns:
            Compressed content
        """
        content = document.get("content", "")
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
        if len(sentences) <= max_sentences:
            return content.strip()

        query_tokens = set(self._tokenize(query))
        scored_sentences = []
        for index, sentence in enumerate(sentences):
            sentence_tokens = set(self._tokenize(sentence))
            overlap = len(query_tokens & sentence_tokens)
            density = overlap / max(len(query_tokens), 1) if query_tokens else 0
            base_score = document.get("reranking_score") or document.get("hybrid_score") or 0
            position_bonus = max(0.0, 1 - (index * 0.08))
            score = (1.5 * density) + (0.4 * position_bonus) + (0.2 * float(base_score))
            scored_sentences.append((index, sentence, score))

        top_indices = sorted(
            [item[0] for item in sorted(scored_sentences, key=lambda item: item[2], reverse=True)[:max_sentences]]
        )
        compressed = " ".join(sentences[i] for i in top_indices).strip()
        return compressed or content.strip()
    
    def optimize_context(self, documents: List[Dict], query: str = "", compression: bool = True,
                        dedup: bool = True, min_relevance: float = 0.3, max_docs: int = 4) -> Tuple[List[Dict], Dict]:
        """
        Optimize context by filtering, deduplicating, and compressing
        
        Args:
            documents: Retrieved documents
            compression: Whether to compress documents
            dedup: Whether to remove redundancy
            min_relevance: Minimum relevance threshold
            
        Returns:
            Tuple of (optimized_documents, optimization_stats)
        """
        start_time = time.time()
        original_count = len(documents)
        original_tokens = sum(len(d.get("content", "").split()) for d in documents)
        
        # Step 1: Filter by relevance
        filtered_docs = self.filter_by_relevance(documents, min_score=min_relevance)
        
        # Step 2: Remove redundancy
        if dedup:
            filtered_docs = self.remove_redundancy(filtered_docs)

        # Step 3: Query-aware salience ranking
        if query:
            filtered_docs = self.rank_by_salience(filtered_docs, query)

        if max_docs and len(filtered_docs) > max_docs:
            filtered_docs = filtered_docs[:max_docs]
        
        # Step 4: Compress
        optimized_docs = []
        final_tokens = 0
        for doc in filtered_docs:
            if compression:
                compressed_content = self.compress_document(doc, query=query, max_sentences=4)
            else:
                compressed_content = doc.get("content", "")
            
            final_tokens += len(compressed_content.split())
            
            optimized_docs.append({
                **doc,
                "original_content": doc.get("content", ""),
                "content": compressed_content,
                "compressed": compression,
            })
        
        latency = (time.time() - start_time) * 1000
        
        stats = {
            "original_docs": original_count,
            "optimized_docs": len(optimized_docs),
            "original_tokens": original_tokens,
            "final_tokens": final_tokens,
            "token_reduction": (1 - final_tokens / original_tokens) if original_tokens > 0 else 0,
            "compression_ratio": final_tokens / original_tokens if original_tokens > 0 else 1.0,
            "latency_ms": latency,
            "applied_filters": ["relevance", "deduplication" if dedup else "", "salience" if query else "", "compression" if compression else ""]
        }
        
        return optimized_docs, stats
    
    def rank_by_salience(self, documents: List[Dict], query: str) -> List[Dict]:
        """
        Rank documents by salience to the query
        
        Args:
            documents: List of documents
            query: Query string
            
        Returns:
            Documents ranked by salience
        """
        query_tokens = set(query.lower().split())
        
        salience_scores = []
        for doc in documents:
            content = doc.get("content", "").lower()
            content_tokens = set(content.split())
            
            # Calculate token overlap ratio
            overlap = len(query_tokens & content_tokens)
            salience = overlap / len(query_tokens) if query_tokens else 0
            
            salience_scores.append((doc, salience))
        
        # Sort by salience
        salience_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, _ in salience_scores]


class ContextCompressor:
    """Advanced context compression strategies"""
    
    def __init__(self):
        self.max_context_tokens = 4000
    
    def summarize_extractive(self, document: Dict, num_sentences: int = 3) -> str:
        """
        Extractive summarization - select key sentences
        
        Args:
            document: Document dict
            num_sentences: Number of sentences to extract
            
        Returns:
            Summarized text
        """
        content = document.get("content", "")
        sentences = content.split('. ')
        
        # Simple scoring: position + length + query relevance
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            # Position score (earlier is better)
            position_score = 1.0 / (i + 1)
            # Length score (prefer medium-length sentences)
            length_score = min(len(sentence.split()), 20) / 20
            
            score = 0.6 * position_score + 0.4 * length_score
            scored_sentences.append((sentence, score))
        
        # Get top sentences maintaining order
        top_indices = sorted(
            range(len(scored_sentences)),
            key=lambda i: scored_sentences[i][1],
            reverse=True
        )[:num_sentences]
        top_indices.sort()
        
        summary = '. '.join(scored_sentences[i][0] for i in top_indices)
        
        return summary
    
    def get_context_within_token_limit(self, documents: List[Dict], max_tokens: int = 4000) -> str:
        """
        Build context string within token limit
        
        Args:
            documents: List of documents
            max_tokens: Maximum tokens allowed
            
        Returns:
            Context string respecting token limit
        """
        context_parts = []
        current_tokens = 0
        
        for doc in documents:
            content = doc.get("content", "")
            tokens = len(content.split())
            
            if current_tokens + tokens <= max_tokens:
                context_parts.append(f"[{doc.get('doc_name', 'Unknown')}]\n{content}")
                current_tokens += tokens
            else:
                # Try to fit partial content
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 50:
                    truncated_content = ' '.join(content.split()[:remaining_tokens])
                    context_parts.append(f"[{doc.get('doc_name', 'Unknown')}]\n{truncated_content}...")
                break
        
        return "\n\n".join(context_parts)


if __name__ == "__main__":
    print("Context Optimizer modules initialized")
