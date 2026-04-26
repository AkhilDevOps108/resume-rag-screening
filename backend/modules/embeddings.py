"""
Embeddings Module
Generates embeddings for documents and queries
Uses sentence-transformers for semantic embeddings
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import json
import os
from pathlib import Path
from threading import Lock
import pickle
from sklearn.feature_extraction.text import HashingVectorizer


class EmbeddingModel:
    """Wrapper for sentence-transformer embeddings"""

    _shared_models = {}
    _model_lock = Lock()
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.model = None
        self.embedding_dim = None
        self.backend = "sentence-transformers"
        self._fallback_vectorizer = None
        self.force_local = os.getenv("EMBEDDING_FORCE_LOCAL", "false").strip().lower() in {
            "1", "true", "yes", "on"
        }

        if self.force_local:
            self._enable_local_fallback()
            return

        self._load_model()

    def _load_model(self):
        """Load model once per process and reuse it across instances."""
        with self._model_lock:
            if self.model_name in self._shared_models:
                shared_model, shared_dim = self._shared_models[self.model_name]
                self.model = shared_model
                self.embedding_dim = shared_dim
                self.backend = "sentence-transformers"
                return

            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(self.model_name)
                embedding_dim = model.get_sentence_embedding_dimension()
                self._shared_models[self.model_name] = (model, embedding_dim)
                self.model = model
                self.embedding_dim = embedding_dim
                self.backend = "sentence-transformers"
            except ImportError:
                raise ImportError("sentence-transformers required. Install with: pip install sentence-transformers")
            except Exception as exc:
                print(f"Failed to load sentence-transformer model '{self.model_name}'. Falling back to local hashing embeddings. Error: {exc}")
                self._enable_local_fallback()

    def _enable_local_fallback(self):
        """Enable deterministic local embeddings that do not require network access."""
        self.backend = "local-hash"
        self.embedding_dim = 512
        self._fallback_vectorizer = HashingVectorizer(
            n_features=self.embedding_dim,
            alternate_sign=False,
            norm='l2',
            analyzer='word',
            lowercase=True,
        )

    def _reinitialize_model(self):
        """Force model reinitialization, useful after transport/client closure errors."""
        if self.backend == "local-hash":
            return

        with self._model_lock:
            if self.model_name in self._shared_models:
                del self._shared_models[self.model_name]
        self._load_model()

    def _local_embed_batch(self, texts: List[str]) -> np.ndarray:
        if self._fallback_vectorizer is None:
            self._enable_local_fallback()
        matrix = self._fallback_vectorizer.transform(texts)
        return matrix.toarray().astype(np.float32)
    
    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string"""
        if self.backend == "local-hash":
            return self._local_embed_batch([text])[0]

        try:
            return self.model.encode(text, convert_to_numpy=True)
        except Exception as exc:
            if "client has been closed" in str(exc).lower():
                self._reinitialize_model()
                if self.backend == "local-hash":
                    return self._local_embed_batch([text])[0]
                return self.model.encode(text, convert_to_numpy=True)
            raise
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed multiple texts"""
        if self.backend == "local-hash":
            return self._local_embed_batch(texts)

        try:
            return self.model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
        except Exception as exc:
            if "client has been closed" in str(exc).lower():
                self._reinitialize_model()
                if self.backend == "local-hash":
                    return self._local_embed_batch(texts)
                return self.model.encode(texts, batch_size=batch_size, convert_to_numpy=True)
            raise
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        from sklearn.metrics.pairwise import cosine_similarity
        return float(cosine_similarity([embedding1], [embedding2])[0][0])
    
    def batch_similarity(self, embedding1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity between one embedding and multiple embeddings"""
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity([embedding1], embeddings2)[0]


class VectorStore:
    """Vector store using FAISS or in-memory storage"""
    
    def __init__(self, embedding_dim: int, use_faiss: bool = True):
        self.embedding_dim = embedding_dim
        self.use_faiss = use_faiss
        self.embeddings = []
        self.chunk_metadata = []  # Store metadata for each embedding
        
        if use_faiss:
            try:
                import faiss
                self.index = faiss.IndexFlatL2(embedding_dim)
            except ImportError:
                print("FAISS not available, using in-memory storage")
                self.use_faiss = False
                self.index = None
        else:
            self.index = None
    
    def add(self, embeddings: np.ndarray, metadata: List[Dict]):
        """Add embeddings to the store"""
        if self.use_faiss and self.index is not None:
            # FAISS uses L2 distance, we'll convert to float32
            embeddings_f32 = embeddings.astype('float32')
            self.index.add(embeddings_f32)
        else:
            self.embeddings.extend(embeddings)
        
        self.chunk_metadata.extend(metadata)
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> Tuple[List[Dict], List[float]]:
        """Search for top-k similar embeddings"""
        if self.use_faiss and self.index is not None:
            query_f32 = query_embedding.astype('float32').reshape(1, -1)
            distances, indices = self.index.search(query_f32, min(k, len(self.chunk_metadata)))
            
            results = []
            scores = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1:
                    # Convert L2 distance to cosine similarity
                    # L2 distance ≈ 2 - 2*cosine_similarity for normalized vectors
                    similarity = 1 - (distance / 2)
                    results.append(self.chunk_metadata[int(idx)])
                    scores.append(float(similarity))
            
            return results, scores
        else:
            # In-memory search using cosine similarity
            if not self.embeddings:
                return [], []
            
            embeddings_array = np.array(self.embeddings)
            similarities = np.dot(embeddings_array, query_embedding) / (
                np.linalg.norm(embeddings_array, axis=1) * np.linalg.norm(query_embedding) + 1e-9
            )
            
            # Get top-k
            top_k_indices = np.argsort(similarities)[-k:][::-1]
            results = [self.chunk_metadata[i] for i in top_k_indices]
            scores = [float(similarities[i]) for i in top_k_indices]
            
            return results, scores
    
    def get_all_embeddings(self) -> np.ndarray:
        """Get all stored embeddings"""
        if self.use_faiss and self.index is not None:
            return self.index.reconstruct_n(0, self.index.ntotal)
        else:
            return np.array(self.embeddings)
    
    def __len__(self):
        """Return number of embeddings stored"""
        if self.use_faiss and self.index is not None:
            return self.index.ntotal
        else:
            return len(self.embeddings)

    def save(self, directory: str) -> None:
        """Persist vector store contents to disk."""
        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = target_dir / "chunk_metadata.json"
        metadata_path.write_text(json.dumps(self.chunk_metadata, indent=2), encoding="utf-8")

        if self.use_faiss and self.index is not None:
            import faiss
            faiss.write_index(self.index, str(target_dir / "faiss.index"))
            info = {"backend": "faiss", "embedding_dim": self.embedding_dim}
            (target_dir / "store_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
            return

        with open(target_dir / "embeddings.pkl", "wb") as fh:
            pickle.dump(np.array(self.embeddings), fh)
        info = {"backend": "in-memory", "embedding_dim": self.embedding_dim}
        (target_dir / "store_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    def load(self, directory: str) -> None:
        """Load vector store contents from disk."""
        target_dir = Path(directory)
        metadata_path = target_dir / "chunk_metadata.json"
        if not metadata_path.exists():
            return

        self.chunk_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        faiss_path = target_dir / "faiss.index"
        if self.use_faiss and self.index is not None and faiss_path.exists():
            import faiss
            self.index = faiss.read_index(str(faiss_path))
            return

        embeddings_path = target_dir / "embeddings.pkl"
        if embeddings_path.exists():
            with open(embeddings_path, "rb") as fh:
                loaded = pickle.load(fh)
            self.embeddings = list(np.array(loaded))


class EmbeddingStore:
    """Manages embeddings and vector storage"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", persistence_dir: Optional[str] = None):
        self.embedding_model = EmbeddingModel(model_name)
        self.vector_store = VectorStore(
            embedding_dim=self.embedding_model.embedding_dim,
            use_faiss=True
        )
        self.persistence_dir = persistence_dir
        self._known_hashes = set()
    
    def add_chunks(self, chunks: List) -> Dict:
        """Add document chunks to the store"""
        unique_chunks = []
        for chunk in chunks:
            content_hash = getattr(chunk, "metadata", {}).get("content_hash")
            if content_hash and content_hash in self._known_hashes:
                continue
            if content_hash:
                self._known_hashes.add(content_hash)
            unique_chunks.append(chunk)

        if not unique_chunks:
            return {
                "chunks_added": 0,
                "chunks_skipped": len(chunks),
                "total_chunks": len(self.vector_store),
                "embedding_dim": self.embedding_model.embedding_dim,
            }

        # Extract texts and metadata from chunks
        texts = [chunk.content for chunk in unique_chunks]
        metadata = [
            {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "doc_name": chunk.doc_name,
                "chunk_idx": chunk.chunk_idx,
                "content": chunk.content,
                "metadata": chunk.metadata
            }
            for chunk in unique_chunks
        ]
        
        # Generate embeddings
        embeddings = self.embedding_model.embed_batch(texts)
        
        # Store in vector database
        self.vector_store.add(embeddings, metadata)
        
        return {
            "chunks_added": len(unique_chunks),
            "chunks_skipped": len(chunks) - len(unique_chunks),
            "total_chunks": len(self.vector_store),
            "embedding_dim": self.embedding_model.embedding_dim
        }

    def save(self, directory: Optional[str] = None) -> None:
        """Persist embedding store to disk."""
        target_dir = directory or self.persistence_dir
        if not target_dir:
            return

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        self.vector_store.save(str(target))

    def load(self, directory: Optional[str] = None) -> bool:
        """Load embedding store from disk if available."""
        target_dir = directory or self.persistence_dir
        if not target_dir:
            return False

        target = Path(target_dir)
        if not target.exists():
            return False

        self.vector_store.load(str(target))
        self._known_hashes = {
            (meta.get("metadata") or {}).get("content_hash")
            for meta in self.vector_store.chunk_metadata
            if (meta.get("metadata") or {}).get("content_hash")
        }
        return len(self.vector_store) > 0
    
    def retrieve(self, query: str, k: int = 5) -> Tuple[List[Dict], List[float]]:
        """Retrieve top-k chunks for a query"""
        # Embed query
        query_embedding = self.embedding_model.embed_text(query)
        
        # Search
        results, scores = self.vector_store.search(query_embedding, k=k)
        
        return results, scores
    
    def batch_retrieve(self, queries: List[str], k: int = 5) -> List[Tuple[List[Dict], List[float]]]:
        """Retrieve for multiple queries"""
        query_embeddings = self.embedding_model.embed_batch(queries)
        results = []
        
        for query_embedding in query_embeddings:
            result_chunks, scores = self.vector_store.search(query_embedding, k=k)
            results.append((result_chunks, scores))
        
        return results
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text"""
        return self.embedding_model.embed_text(text)
    
    def get_all_embeddings(self) -> np.ndarray:
        """Get all stored embeddings"""
        return self.vector_store.get_all_embeddings()
    
    def get_chunk_metadata(self, chunk_id: str) -> Optional[Dict]:
        """Get metadata for a specific chunk"""
        for metadata in self.vector_store.chunk_metadata:
            if metadata.get("chunk_id") == chunk_id:
                return metadata
        return None


if __name__ == "__main__":
    # Test initialization
    store = EmbeddingStore()
    print(f"Embedding store initialized with model: sentence-transformers/all-MiniLM-L6-v2")
    print(f"Embedding dimension: {store.embedding_model.embedding_dim}")
