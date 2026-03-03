#!/usr/bin/env python3
"""
rag_store.py - Vector store wrapper for semantic memory search.
Supports ChromaDB and FAISS as backends, with hybrid search capability.
"""
import os
import json
import hashlib
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from embedder import Embedder, get_embedder

# Default storage location
DEFAULT_STORAGE_DIR = Path.home() / ".openclaw" / "memory_vectors"


@dataclass
class MemoryChunk:
    """A chunk of memory with embedding and metadata."""
    id: str
    content: str
    embedding: List[float]
    chunk_index: int
    total_chunks: int
    source: str
    created_at: str
    metadata: Dict[str, Any]


class RAGStore:
    """Vector-based memory store with hybrid search."""
    
    def __init__(
        self,
        storage_dir: Path = None,
        embedder: Embedder = None,
        backend: str = "chroma",
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        Initialize RAG store.
        
        Args:
            storage_dir: Directory to persist vectors
            embedder: Embedder instance for generating vectors
            backend: "chroma", "faiss", or "simple" (in-memory)
            chunk_size: Characters per chunk for auto-chunking
            chunk_overlap: Overlap between chunks
        """
        self.storage_dir = storage_dir or DEFAULT_STORAGE_DIR
        self.embedder = embedder or Embedder()
        self.backend = backend
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self._vector_store = None
        self._memories: Dict[str, MemoryChunk] = {}
        self._index_loaded = False
        
    def _get_storage_path(self) -> Path:
        """Get the storage path for this store."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        return self.storage_dir
    
    def _init_backend(self):
        """Initialize the vector store backend."""
        if self._vector_store is not None:
            return
            
        if self.backend == "chroma":
            self._init_chroma()
        elif self.backend == "faiss":
            self._init_faiss()
        else:
            self._init_simple()
    
    def _init_chroma(self):
        """Initialize ChromaDB backend."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            storage_path = self._get_storage_path() / "chroma"
            storage_path.mkdir(parents=True, exist_ok=True)
            
            self._chroma_client = chromadb.PersistentClient(path=str(storage_path))
            self._vector_store = self._chroma_client.get_or_create_collection(
                name="memory",
                metadata={"hnsw:space": "cosine"}
            )
        except ImportError:
            print("ChromaDB not installed, falling back to simple backend")
            self.backend = "simple"
            self._init_simple()
    
    def _init_faiss(self):
        """Initialize FAISS backend."""
        try:
            import faiss
            import numpy as np
            
            self._faiss = faiss
            self._np = np
            dim = self.embedder.get_embedding_dimension()
            self._vector_store = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized)
            self._metadata_store = {}
        except ImportError:
            print("FAISS not installed, falling back to simple backend")
            self.backend = "simple"
            self._init_simple()
    
    def _init_simple(self):
        """Initialize simple in-memory backend."""
        self._vector_store = {}  # id -> embedding
        self._metadata_store = {}  # id -> metadata
    
    def load_index(self):
        """Load existing index from disk."""
        if self._index_loaded:
            return
            
        self._init_backend()
        
        index_file = self._get_storage_path() / "memories.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                data = json.load(f)
                for chunk_data in data.get("memories", []):
                    chunk = MemoryChunk(**chunk_data)
                    self._memories[chunk.id] = chunk
                    
                    if self.backend == "chroma":
                        self._vector_store.upsert(
                            ids=[chunk.id],
                            embeddings=[chunk.embedding],
                            metadatas=[{"source": chunk.source, "created_at": chunk.created_at}]
                        )
                    elif self.backend == "faiss":
                        import numpy as np
                        emb = np.array([chunk.embedding], dtype='float32')
                        # Normalize for cosine similarity
                        norm = np.linalg.norm(emb)
                        if norm > 0:
                            emb = emb / norm
                        self._vector_store.add(emb)
                        self._metadata_store[len(self._memories) - 1] = chunk.id
        
        self._index_loaded = True
    
    def save_index(self):
        """Persist index to disk."""
        index_file = self._get_storage_path() / "memories.json"
        
        data = {
            "memories": [asdict(chunk) for chunk in self._memories.values()],
            "backend": self.backend,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap
        }
        
        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into overlapping chunks.
        
        Returns:
            List of (chunk_text, start_idx, end_idx)
        """
        if len(text) <= self.chunk_size:
            return [(text, 0, len(text))]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at word boundary
            if end < len(text):
                # Look for last space or newline
                last_space = max(text.rfind(' ', 0, end), text.rfind('\n', 0, end))
                if last_space > start:
                    end = last_space
            
            chunks.append((text[start:end], start, min(end, len(text))))
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
    
    def _generate_id(self, content: str, source: str, chunk_index: int) -> str:
        """Generate unique ID for a chunk."""
        raw = f"{source}:{chunk_index}:{content[:100]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def add(
        self,
        content: str,
        source: str = "default",
        metadata: Dict[str, Any] = None
    ) -> List[str]:
        """
        Add a memory to the store with auto-chunking.
        
        Args:
            content: Text content to store
            source: Source identifier (e.g., "conversation", "task", "learned")
            metadata: Additional metadata
            
        Returns:
            List of chunk IDs added
        """
        self._init_backend()
        self.load_index()
        
        chunks = self._chunk_text(content)
        chunk_ids = []
        timestamp = datetime.now().isoformat()
        
        # Generate embeddings for all chunks at once
        texts = [c[0] for c in chunks]
        embeddings = self.embedder.embed_batch(texts)
        
        for i, (chunk_text, start, end) in enumerate(chunks):
            chunk_id = self._generate_id(chunk_text, source, i)
            
            chunk = MemoryChunk(
                id=chunk_id,
                content=chunk_text,
                embedding=embeddings[i],
                chunk_index=i,
                total_chunks=len(chunks),
                source=source,
                created_at=timestamp,
                metadata=metadata or {}
            )
            
            self._memories[chunk_id] = chunk
            chunk_ids.append(chunk_id)
            
            # Add to backend
            if self.backend == "chroma":
                self._vector_store.upsert(
                    ids=[chunk_id],
                    embeddings=[embeddings[i]],
                    metadatas=[{"source": source, "created_at": timestamp}]
                )
            elif self.backend == "faiss":
                import numpy as np
                emb = np.array([embeddings[i]], dtype='float32')
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                self._vector_store.add(emb)
                self._metadata_store[len(self._memories) - 1] = chunk_id
        
        self.save_index()
        return chunk_ids
    
    def search(
        self,
        query: str,
        k: int = 5,
        source_filter: str = None,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: combines vector similarity with keyword matching.
        
        Args:
            query: Search query
            k: Number of results
            source_filter: Optional source to filter by
            alpha: Weight for vector search (1-alpha for keyword)
            
        Returns:
            List of dicts with content, score, source, created_at
        """
        self._init_backend()
        self.load_index()
        
        if not self._memories:
            return []
        
        # Vector search
        query_embedding = self.embedder.embed(query)
        vector_results = self._vector_search(query_embedding, k * 2, source_filter)
        
        # Keyword search
        keyword_results = self._keyword_search(query, k * 2, source_filter)
        
        # Combine with reranking
        combined = self._hybrid_rerank(
            vector_results, keyword_results, k, alpha
        )
        
        return [
            {
                "content": self._memories[chunk_id].content,
                "score": score,
                "source": self._memories[chunk_id].source,
                "created_at": self._memories[chunk_id].created_at,
                "chunk_index": self._memories[chunk_id].chunk_index,
                "total_chunks": self._memories[chunk_id].total_chunks
            }
            for chunk_id, score in combined
        ]
    
    def _vector_search(
        self,
        query_embedding: List[float],
        k: int,
        source_filter: str = None
    ) -> List[Tuple[str, float]]:
        """Perform vector similarity search."""
        import numpy as np
        
        results = []
        
        if self.backend == "chroma":
            query = np.array([query_embedding])
            results_raw = self._vector_store.query(
                query_embeddings=query,
                n_results=k,
                where={"source": source_filter} if source_filter else None
            )
            for i, doc_id in enumerate(results_raw["ids"][0]):
                score = 1 - results_raw["distances"][0][i]  # Convert distance to similarity
                results.append((doc_id, score))
                
        elif self.backend == "faiss":
            query = np.array([query_embedding], dtype='float32')
            norm = np.linalg.norm(query)
            if norm > 0:
                query = query / norm
            distances, indices = self._vector_store.search(query, k)
            for i, idx in enumerate(indices[0]):
                if idx >= 0:
                    chunk_id = self._metadata_store.get(idx)
                    if chunk_id:
                        score = float(1 / (1 + distances[0][i]))  # Convert distance to similarity
                        results.append((chunk_id, score))
        else:
            # Simple in-memory search
            query_arr = np.array(query_embedding)
            for chunk_id, chunk in self._memories.items():
                if source_filter and chunk.source != source_filter:
                    continue
                emb_arr = np.array(chunk.embedding)
                # Cosine similarity
                norm_q = np.linalg.norm(query_arr)
                norm_e = np.linalg.norm(emb_arr)
                if norm_q > 0 and norm_e > 0:
                    score = np.dot(query_arr, emb_arr) / (norm_q * norm_e)
                    results.append((chunk_id, float(score)))
            
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:k]
        
        return results
    
    def _keyword_search(
        self,
        query: str,
        k: int,
        source_filter: str = None
    ) -> List[Tuple[str, float]]:
        """Simple keyword/BM25-like search."""
        # Simple term frequency approach
        query_terms = re.findall(r'\w+', query.lower())
        if not query_terms:
            return []
        
        results = []
        
        for chunk_id, chunk in self._memories.items():
            if source_filter and chunk.source != source_filter:
                continue
                
            content_lower = chunk.content.lower()
            
            # Count matching terms
            matches = sum(1 for term in query_terms if term in content_lower)
            score = matches / len(query_terms)  # Normalize by query length
            
            # Boost by chunk completeness (prefer complete thoughts)
            if chunk.chunk_index == chunk.total_chunks - 1:
                score *= 1.1
                
            if score > 0:
                results.append((chunk_id, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
    
    def _hybrid_rerank(
        self,
        vector_results: List[Tuple[str, float]],
        keyword_results: List[Tuple[str, float]],
        k: int,
        alpha: float
    ) -> List[Tuple[str, float]]:
        """Combine vector and keyword results."""
        scores = {}
        
        # Add vector scores
        for chunk_id, score in vector_results:
            scores[chunk_id] = scores.get(chunk_id, 0) + alpha * score
        
        # Add keyword scores
        for chunk_id, score in keyword_results:
            scores[chunk_id] = scores.get(chunk_id, 0) + (1 - alpha) * score
        
        # Sort and return top k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:k]
    
    def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory chunk."""
        self.load_index()
        
        if chunk_id not in self._memories:
            return None
            
        chunk = self._memories[chunk_id]
        return {
            "id": chunk.id,
            "content": chunk.content,
            "source": chunk.source,
            "created_at": chunk.created_at,
            "metadata": chunk.metadata,
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks
        }
    
    def delete(self, source: str = None, older_than: str = None) -> int:
        """
        Delete memories by source or age.
        
        Args:
            source: Delete all chunks from this source
            older_than: ISO date string, delete chunks older than this
            
        Returns:
            Number of chunks deleted
        """
        self.load_index()
        
        to_delete = []
        
        for chunk_id, chunk in self._memories.items():
            if source and chunk.source != source:
                continue
            if older_than and chunk.created_at >= older_than:
                continue
            to_delete.append(chunk_id)
        
        for chunk_id in to_delete:
            del self._memories[chunk_id]
        
        if to_delete:
            self.save_index()
        
        return len(to_delete)
    
    def list_sources(self) -> List[str]:
        """List all memory sources."""
        self.load_index()
        return list(set(chunk.source for chunk in self._memories.values()))
    
    def stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        self.load_index()
        
        sources = self.list_sources()
        source_counts = {}
        for source in sources:
            source_counts[source] = sum(
                1 for c in self._memories.values() if c.source == source
            )
        
        return {
            "total_chunks": len(self._memories),
            "sources": source_counts,
            "backend": self.backend,
            "embedding_dim": self.embedder.get_embedding_dimension()
        }


def get_rag_store(config: Optional[dict] = None) -> RAGStore:
    """
    Factory function to create RAG store from config.
    
    Args:
        config: Optional config dict with keys:
            - storage_dir: Path for persistence
            - embedder: Embedder config
            - backend: "chroma", "faiss", or "simple"
            - chunk_size: Characters per chunk
            - chunk_overlap: Overlap between chunks
    
    Returns:
        RAGStore instance
    """
    if config is None:
        config = {}
    
    storage_dir = config.get("storage_dir")
    if storage_dir:
        storage_dir = Path(storage_dir)
    
    embedder_config = config.get("embedder")
    embedder = get_embedder(embedder_config) if embedder_config else None
    
    return RAGStore(
        storage_dir=storage_dir,
        embedder=embedder,
        backend=config.get("backend", "simple"),
        chunk_size=config.get("chunk_size", 512),
        chunk_overlap=config.get("chunk_overlap", 50)
    )


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="RAG Memory Store CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Add command
    parser_add = subparsers.add_parser("add", help="Add memory")
    parser_add.add_argument("content", type=str, help="Content to store")
    parser_add.add_argument("--source", default="cli", help="Source identifier")
    parser_add.add_argument("--backend", choices=["chroma", "faiss", "simple"], default="simple")
    
    # Search command
    parser_search = subparsers.add_parser("search", help="Search memories")
    parser_search.add_argument("query", type=str, help="Search query")
    parser_search.add_argument("--k", type=int, default=5, help="Number of results")
    parser_search.add_argument("--source", help="Filter by source")
    parser_search.add_argument("--alpha", type=float, default=0.7, help="Vector weight (1-alpha for keyword)")
    
    # Stats command
    subparsers.add_parser("stats", help="Show store statistics")
    
    # List sources
    subparsers.add_parser("sources", help="List memory sources")
    
    # Delete command
    parser_delete = subparsers.add_parser("delete", help="Delete memories")
    parser_delete.add_argument("--source", help="Delete by source")
    parser_delete.add_argument("--older-than", help="Delete older than date")
    
    args = parser.parse_args()
    
    store = RAGStore(backend=args.backend)
    
    if args.command == "add":
        chunk_ids = store.add(args.content, args.source)
        print(json.dumps({"added": len(chunk_ids), "chunk_ids": chunk_ids}))
        
    elif args.command == "search":
        results = store.search(args.query, args.k, args.source, args.alpha)
        print(json.dumps(results, indent=2))
        
    elif args.command == "stats":
        print(json.dumps(store.stats(), indent=2))
        
    elif args.command == "sources":
        print(json.dumps(store.list_sources()))
        
    elif args.command == "delete":
        count = store.delete(args.source, args.older_than)
        print(json.dumps({"deleted": count}))
