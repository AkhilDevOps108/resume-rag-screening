"""
Semantic Graph Module
Builds a semantic graph of chunk relationships for context-aware retrieval
"""

from typing import List, Dict, Tuple, Set
import numpy as np
import networkx as nx
import time


class SemanticGraph:
    """Builds and manages semantic relationships between document chunks"""
    
    def __init__(self, embedding_store):
        """
        Initialize semantic graph
        
        Args:
            embedding_store: EmbeddingStore instance for computing similarities
        """
        self.embedding_store = embedding_store
        self.graph = nx.DiGraph()
        self.embeddings_cache = {}
        self.similarity_threshold = 0.5
    
    def add_chunks(self, chunks: List, chunk_metadata: List[Dict]) -> None:
        """
        Build semantic graph from chunks
        
        Args:
            chunks: List of document chunks
            chunk_metadata: List of chunk metadata dicts
        """
        # Add nodes for each chunk
        for metadata in chunk_metadata:
            chunk_id = metadata["chunk_id"]
            self.graph.add_node(
                chunk_id,
                content=metadata.get("content", ""),
                doc_id=metadata.get("doc_id", ""),
                doc_name=metadata.get("doc_name", ""),
                chunk_idx=metadata.get("chunk_idx", 0),
            )
        
        # Build edges based on semantic similarity
        self._build_semantic_edges(chunk_metadata)
        
        # Add document structure edges (consecutive chunks in same document)
        self._build_structural_edges(chunk_metadata)
    
    def _build_semantic_edges(self, chunk_metadata: List[Dict], top_k: int = 3) -> None:
        """
        Build edges based on semantic similarity between chunks
        
        Args:
            chunk_metadata: List of chunk metadata
            top_k: Number of semantic neighbors per chunk
        """
        chunk_ids = [m["chunk_id"] for m in chunk_metadata]
        
        for i, metadata in enumerate(chunk_metadata):
            chunk_id = metadata["chunk_id"]
            content = metadata.get("content", "")
            
            # Get embedding for this chunk
            embedding = self.embedding_store.get_embedding(content)
            self.embeddings_cache[chunk_id] = embedding
            
            # Find most similar chunks
            similarities = []
            for j, other_metadata in enumerate(chunk_metadata):
                if i == j:
                    continue
                
                other_chunk_id = other_metadata["chunk_id"]
                other_content = other_metadata.get("content", "")
                
                # Get embedding for other chunk
                if other_chunk_id not in self.embeddings_cache:
                    other_embedding = self.embedding_store.get_embedding(other_content)
                    self.embeddings_cache[other_chunk_id] = other_embedding
                else:
                    other_embedding = self.embeddings_cache[other_chunk_id]
                
                # Calculate cosine similarity
                similarity = np.dot(embedding, other_embedding) / (
                    np.linalg.norm(embedding) * np.linalg.norm(other_embedding) + 1e-9
                )
                
                if similarity >= self.similarity_threshold:
                    similarities.append((other_chunk_id, similarity))
            
            # Add edges to top-k similar chunks
            similarities.sort(key=lambda x: x[1], reverse=True)
            for other_chunk_id, similarity in similarities[:top_k]:
                self.graph.add_edge(
                    chunk_id,
                    other_chunk_id,
                    weight=similarity,
                    edge_type="semantic"
                )
    
    def _build_structural_edges(self, chunk_metadata: List[Dict]) -> None:
        """
        Build edges based on document structure (consecutive chunks)
        
        Args:
            chunk_metadata: List of chunk metadata
        """
        # Group chunks by document
        doc_chunks = {}
        for metadata in chunk_metadata:
            doc_id = metadata.get("doc_id", "")
            chunk_idx = metadata.get("chunk_idx", 0)
            chunk_id = metadata.get("chunk_id", "")
            
            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = []
            doc_chunks[doc_id].append((chunk_idx, chunk_id))
        
        # Add edges between consecutive chunks
        for doc_id, chunks in doc_chunks.items():
            chunks.sort()  # Sort by chunk index
            for i in range(len(chunks) - 1):
                current_chunk_id = chunks[i][1]
                next_chunk_id = chunks[i + 1][1]
                
                self.graph.add_edge(
                    current_chunk_id,
                    next_chunk_id,
                    weight=0.8,
                    edge_type="structural"
                )
    
    def get_neighbors(self, chunk_id: str, hops: int = 1) -> Dict[str, List[str]]:
        """
        Get semantic neighbors of a chunk
        
        Args:
            chunk_id: Chunk ID to get neighbors for
            hops: Number of hops to traverse
            
        Returns:
            Dictionary with neighbors at each hop level
        """
        neighbors = {"hop_0": [chunk_id]}
        visited = {chunk_id}
        current_level = [chunk_id]
        
        for hop in range(1, hops + 1):
            next_level = []
            for current_chunk in current_level:
                if current_chunk in self.graph:
                    for neighbor in self.graph.successors(current_chunk):
                        if neighbor not in visited:
                            next_level.append(neighbor)
                            visited.add(neighbor)
            
            neighbors[f"hop_{hop}"] = next_level
            current_level = next_level
        
        return neighbors
    
    def get_subgraph(self, chunk_ids: List[str], expand_by_hops: int = 1) -> nx.DiGraph:
        """
        Extract a subgraph centered on specific chunks
        
        Args:
            chunk_ids: Central chunk IDs
            expand_by_hops: Number of hops to expand
            
        Returns:
            Subgraph as networkx DiGraph
        """
        relevant_nodes = set(chunk_ids)
        
        # Expand by hops
        for chunk_id in chunk_ids:
            neighbors_dict = self.get_neighbors(chunk_id, hops=expand_by_hops)
            for hop_level in neighbors_dict.values():
                relevant_nodes.update(hop_level)
        
        # Extract subgraph
        subgraph = self.graph.subgraph(relevant_nodes).copy()
        
        return subgraph
    
    def find_paths(self, source_chunk_id: str, target_chunk_id: str, max_length: int = 3) -> List[List[str]]:
        """
        Find paths between two chunks
        
        Args:
            source_chunk_id: Starting chunk
            target_chunk_id: Target chunk
            max_length: Maximum path length
            
        Returns:
            List of paths (each path is a list of chunk IDs)
        """
        paths = []
        try:
            # Find all simple paths up to max_length
            all_paths = nx.all_simple_paths(
                self.graph,
                source_chunk_id,
                target_chunk_id,
                cutoff=max_length
            )
            paths = list(all_paths)
        except nx.NetworkXNoPath:
            pass
        
        return paths
    
    def rank_by_centrality(self, chunk_ids: List[str]) -> List[Tuple[str, float]]:
        """
        Rank chunks by graph centrality measures
        
        Args:
            chunk_ids: List of chunk IDs to rank
            
        Returns:
            List of (chunk_id, centrality_score) tuples sorted by score
        """
        # Calculate various centrality measures
        in_degree = dict(self.graph.in_degree())
        out_degree = dict(self.graph.out_degree())
        
        # Pagerank
        pagerank = nx.pagerank(self.graph)
        
        # Combine scores
        centrality_scores = []
        for chunk_id in chunk_ids:
            if chunk_id in self.graph:
                score = (
                    0.3 * in_degree.get(chunk_id, 0) +
                    0.3 * out_degree.get(chunk_id, 0) +
                    0.4 * pagerank.get(chunk_id, 0) * 10  # Scale pagerank
                )
                centrality_scores.append((chunk_id, score))
        
        centrality_scores.sort(key=lambda x: x[1], reverse=True)
        
        return centrality_scores
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the semantic graph"""
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "avg_degree": 2 * self.graph.number_of_edges() / max(self.graph.number_of_nodes(), 1),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph),
        }


if __name__ == "__main__":
    print("Semantic Graph module initialized")
