#!/usr/bin/env python3
"""
Tests for memory RAG system.
Uses mock embeddings to avoid dependencies on sentence-transformers.
"""
import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from embedder import Embedder, get_embedder
from rag_store import RAGStore, MemoryChunk, get_rag_store


class MockEmbedder(Embedder):
    """Mock embedder for testing - returns deterministic vectors."""
    
    def __init__(self, dimension: int = 384):
        super().__init__(provider="mock")
        self.dimension = dimension
        self._call_count = 0
        
    def embed(self, text: str) -> list[float]:
        self._call_count += 1
        # Generate deterministic mock embedding based on text hash
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # Extend to required dimension
        extended = list(h) * (self.dimension // 32 + 1)
        vec = extended[:self.dimension]
        # Normalize
        norm = sum(x*x for x in vec) ** 0.5
        if norm > 0:
            vec = [x/norm for x in vec]
        return vec
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
    
    def get_embedding_dimension(self) -> int:
        return self.dimension


class TestEmbedder(unittest.TestCase):
    """Tests for the embedder module."""
    
    def test_embedder_creation(self):
        """Test creating an embedder."""
        embedder = Embedder(model="test-model", provider="local")
        self.assertEqual(embedder.model, "test-model")
        self.assertEqual(embedder.provider, "local")
    
    def test_embedder_dimension_fallback(self):
        """Test default dimension fallback."""
        embedder = Embedder(provider="mock", model="unknown")
        dim = embedder.get_embedding_dimension()
        self.assertEqual(dim, 384)
    
    def test_get_embedder_factory(self):
        """Test factory function."""
        config = {"provider": "local", "model": "test"}
        embedder = get_embedder(config)
        self.assertIsInstance(embedder, Embedder)
    
    def test_embedder_empty_text_error(self):
        """Test that empty text raises error."""
        embedder = Embedder(provider="mock")
        with self.assertRaises(ValueError):
            embedder.embed("")


class TestRAGStore(unittest.TestCase):
    """Tests for the RAG store."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.embedder = MockEmbedder()
        
    def tearDown(self):
        """Clean up temp files."""
        shutil.rmtree(self.temp_dir)
    
    def test_store_creation(self):
        """Test creating a RAG store."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        self.assertEqual(store.backend, "simple")
        self.assertEqual(store.chunk_size, 512)
    
    def test_add_single_chunk(self):
        """Test adding a short text (single chunk)."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        chunk_ids = store.add("This is a test memory", source="test")
        
        self.assertEqual(len(chunk_ids), 1)
        self.assertIn(chunk_ids[0], store._memories)
        
        # Check chunk metadata
        chunk = store._memories[chunk_ids[0]]
        self.assertEqual(chunk.content, "This is a test memory")
        self.assertEqual(chunk.source, "test")
        self.assertEqual(chunk.total_chunks, 1)
    
    def test_add_multiple_chunks(self):
        """Test auto-chunking of long text."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple",
            chunk_size=50,
            chunk_overlap=10
        )
        
        long_text = "This is a very long text that should be split into multiple chunks " * 5
        chunk_ids = store.add(long_text, source="test")
        
        # Should have multiple chunks
        self.assertGreater(len(chunk_ids), 1)
        
        # Verify all chunks exist
        for chunk_id in chunk_ids:
            self.assertIn(chunk_id, store._memories)
    
    def test_search_basic(self):
        """Test basic semantic search."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        # Add some memories
        store.add("The cat sat on the mat", source="facts")
        store.add("Dogs love to play fetch", source="facts")
        store.add("Python is a programming language", source="facts")
        
        # Search for cat
        results = store.search("feline pet", k=2)
        
        self.assertGreater(len(results), 0)
        self.assertIn("cat", results[0]["content"].lower())
    
    def test_search_with_source_filter(self):
        """Test search with source filtering."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        store.add("Fact 1", source="facts")
        store.add("Fact 2", source="facts")
        store.add("Note 1", source="notes")
        
        # Filter to only facts
        results = store.search("anything", k=10, source_filter="facts")
        
        self.assertTrue(all(r["source"] == "facts" for r in results))
    
    def test_keyword_search(self):
        """Test keyword-only search via alpha=0."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        store.add("Python programming tutorial", source="code")
        store.add("JavaScript frontend guide", source="code")
        
        # Pure keyword search
        results = store.search("Python", k=5, alpha=0.0)
        
        self.assertGreater(len(results), 0)
        self.assertIn("Python", results[0]["content"])
    
    def test_get_chunk(self):
        """Test retrieving a specific chunk."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        chunk_ids = store.add("Test memory", source="test")
        chunk_id = chunk_ids[0]
        
        retrieved = store.get(chunk_id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["content"], "Test memory")
        self.assertEqual(retrieved["source"], "test")
    
    def test_get_nonexistent_chunk(self):
        """Test retrieving non-existent chunk returns None."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        result = store.get("nonexistent-id")
        self.assertIsNone(result)
    
    def test_delete_by_source(self):
        """Test deleting memories by source."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        store.add("Fact 1", source="facts")
        store.add("Fact 2", source="facts")
        store.add("Note 1", source="notes")
        
        # Delete all facts
        count = store.delete(source="facts")
        
        self.assertEqual(count, 2)
        self.assertEqual(len(store._memories), 1)
        self.assertEqual(list(store._memories.values())[0].source, "notes")
    
    def test_list_sources(self):
        """Test listing all sources."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        store.add("Content 1", source="source_a")
        store.add("Content 2", source="source_b")
        store.add("Content 3", source="source_a")
        
        sources = store.list_sources()
        
        self.assertEqual(set(sources), {"source_a", "source_b"})
    
    def test_stats(self):
        """Test getting store statistics."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        store.add("Fact 1", source="facts")
        store.add("Fact 2", source="facts")
        store.add("Note 1", source="notes")
        
        stats = store.stats()
        
        self.assertEqual(stats["total_chunks"], 3)
        self.assertEqual(stats["sources"]["facts"], 2)
        self.assertEqual(stats["sources"]["notes"], 1)
        self.assertEqual(stats["backend"], "simple")
    
    def test_persistence(self):
        """Test that memories persist after reinitialization."""
        store1 = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        store1.add("Persistent memory", source="test")
        
        # Create new store with same directory
        store2 = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        # Should have loaded from disk
        results = store2.search("memory", k=5)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Persistent memory")


class TestHybridSearch(unittest.TestCase):
    """Tests for hybrid search functionality."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.embedder = MockEmbedder()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_hybrid_combines_vector_and_keyword(self):
        """Test that hybrid search combines both approaches."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple"
        )
        
        # Add memories
        store.add("Python is great", source="code")
        store.add("JavaScript is awesome", source="code")
        
        # Search with alpha=0.5 (balanced)
        results = store.search("Python", k=5, alpha=0.5)
        
        self.assertGreater(len(results), 0)
        # Should find Python-related content
        self.assertIn("Python", results[0]["content"])


class TestAutoChunking(unittest.TestCase):
    """Tests for auto-chunking functionality."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.embedder = MockEmbedder()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_small_text_not_chunked(self):
        """Test that short texts are not chunked."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple",
            chunk_size=512
        )
        
        chunk_ids = store.add("Short text", source="test")
        
        # Should be one chunk
        self.assertEqual(len(chunk_ids), 1)
        self.assertEqual(store._memories[chunk_ids[0]].total_chunks, 1)
    
    def test_large_text_chunked(self):
        """Test that large texts are split."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple",
            chunk_size=100,
            chunk_overlap=20
        )
        
        # Create text larger than chunk size
        text = "A" * 500
        chunk_ids = store.add(text, source="test")
        
        # Should have multiple chunks
        self.assertGreater(len(chunk_ids), 1)
    
    def test_chunk_indices(self):
        """Test that chunk indices are correct."""
        store = RAGStore(
            storage_dir=self.temp_dir,
            embedder=self.embedder,
            backend="simple",
            chunk_size=50,
            chunk_overlap=10
        )
        
        chunk_ids = store.add("This is a longer piece of text that needs chunking", source="test")
        
        for i, chunk_id in enumerate(chunk_ids):
            chunk = store._memories[chunk_id]
            self.assertEqual(chunk.chunk_index, i)
            self.assertEqual(chunk.total_chunks, len(chunk_ids))


class TestFactory(unittest.TestCase):
    """Tests for factory functions."""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_get_rag_store_default(self):
        """Test default RAG store creation."""
        store = get_rag_store()
        self.assertIsInstance(store, RAGStore)
    
    def test_get_rag_store_with_config(self):
        """Test RAG store with config."""
        embedder = MockEmbedder()
        store = get_rag_store({
            "storage_dir": str(self.temp_dir),
            "embedder": {"provider": "mock"},
            "backend": "simple",
            "chunk_size": 256
        })
        
        self.assertIsInstance(store, RAGStore)
        self.assertEqual(store.chunk_size, 256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
