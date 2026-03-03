#!/usr/bin/env python3
"""
embedder.py - Generate embeddings for semantic memory search.
Supports sentence-transformers (local) and OpenAI API.
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional

# Default to sentence-transformers for local embedding
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Cache directory for downloaded models
CACHE_DIR = Path.home() / ".cache" / "openclaw" / "embeddings"


class Embedder:
    """Generate embeddings using configurable backend."""
    
    def __init__(self, model: str = None, provider: str = "local", api_key: Optional[str] = None):
        """
        Initialize embedder.
        
        Args:
            model: Model name (sentence-transformers model name or OpenAI model)
            provider: "local" (sentence-transformers) or "openai"
            api_key: OpenAI API key (if provider="openai")
        """
        self.model = model or DEFAULT_MODEL
        self.provider = provider
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        self._local_model = None
        
    def _get_local_model(self):
        """Lazy load sentence-transformers model."""
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                self._local_model = SentenceTransformer(self.model, cache_folder=str(CACHE_DIR))
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._local_model
    
    def _get_openai_client(self):
        """Lazy init OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client
    
    def embed(self, text: str) -> list[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
            
        if self.provider == "openai":
            return self._embed_openai(text)
        else:
            return self._embed_local(text)
    
    def _embed_local(self, text: str) -> list[float]:
        """Generate embedding using sentence-transformers."""
        model = self._get_local_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _embed_openai(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API."""
        client = self._get_openai_client()
        response = client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        # Filter empty strings
        valid_texts = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not valid_texts:
            return []
            
        indices, filtered_texts = zip(*valid_texts)
        
        if self.provider == "openai":
            embeddings = self._embed_openai_batch(filtered_texts)
        else:
            embeddings = self._embed_local_batch(filtered_texts)
        
        # Reconstruct full list with empty embeddings for skipped texts
        result = []
        text_idx = 0
        for i in range(len(texts)):
            if i in indices:
                result.append(embeddings[indices.index(i)])
                text_idx += 1
            else:
                # Return zeros for empty strings (same dimension as real embeddings)
                dim = len(embeddings[0]) if embeddings else 384
                result.append([0.0] * dim)
                
        return result
    
    def _embed_local_batch(self, texts: tuple) -> list[list[float]]:
        """Batch embed using sentence-transformers."""
        model = self._get_local_model()
        embeddings = model.encode(list(texts), convert_to_numpy=True)
        return [e.tolist() for e in embeddings]
    
    def _embed_openai_batch(self, texts: tuple) -> list[list[float]]:
        """Batch embed using OpenAI API."""
        client = self._get_openai_client()
        response = client.embeddings.create(
            model=self.model,
            input=list(texts)
        )
        return [d.embedding for d in response.data]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embedding vectors for current model."""
        # Common dimensions for popular models
        dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        
        if self.model in dimensions:
            return dimensions[self.model]
        
        # Probe with a test embedding if unknown
        try:
            test_emb = self.embed("test")
            return len(test_emb)
        except Exception:
            return 384  # Default fallback


def get_embedder(config: Optional[dict] = None) -> Embedder:
    """
    Factory function to create embedder from config.
    
    Args:
        config: Optional config dict with keys:
            - provider: "local" or "openai" 
            - model: model name
            - api_key: OpenAI key (if using openai)
    
    Returns:
        Embedder instance
    """
    if config is None:
        config = {}
    
    provider = config.get("provider", "local")
    model = config.get("model")
    api_key = config.get("api_key")
    
    return Embedder(model=model, provider=provider, api_key=api_key)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Embedding CLI")
    parser.add_argument("text", type=str, help="Text to embed")
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--provider", choices=["local", "openai"], default="local", help="Embedding provider")
    parser.add_argument("--batch", action="store_true", help="Read multiple lines from stdin")
    
    args = parser.parse_args()
    
    embedder = Embedder(model=args.model, provider=args.provider)
    
    if args.batch:
        import sys
        texts = [line.strip() for line in sys.stdin if line.strip()]
        embeddings = embedder.embed_batch(texts)
        for emb in embeddings:
            print(json.dumps(emb))
    else:
        embedding = embedder.embed(args.text)
        print(json.dumps(embedding))
