"""Embedding generation."""

import hashlib
from pathlib import Path
from typing import List, Optional
import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings with caching."""

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-base",
        cache_dir: Optional[Path] = None,
        batch_size: int = 32,
        normalize: bool = True,
    ):
        """Initialize generator.

        Args:
            model_name: Model name from Hugging Face
            cache_dir: Cache directory for embeddings
            batch_size: Batch size for encoding
            normalize: Whether to L2 normalize embeddings
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize = normalize

        # Setup cache
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None

        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info(
            f"Model loaded, embedding dimension: {self.model.get_sentence_embedding_dimension()}"
        )

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text.

        Args:
            text: Input text

        Returns:
            Cache key (hash)
        """
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{text_hash}.npy"

    def _load_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """Load embedding from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached embedding or None
        """
        if not self.cache_dir:
            return None

        cache_file = self.cache_dir / cache_key

        if cache_file.exists():
            try:
                return np.load(cache_file)
            except Exception as e:
                logger.warning(f"Error loading cache: {e}")
                return None

        return None

    def _save_to_cache(self, cache_key: str, embedding: np.ndarray):
        """Save embedding to cache.

        Args:
            cache_key: Cache key
            embedding: Embedding array
        """
        if not self.cache_dir:
            return

        cache_file = self.cache_dir / cache_key

        try:
            np.save(cache_file, embedding)
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")

    def embed_texts(self, texts: List[str], use_cache: bool = True) -> np.ndarray:
        """Generate embeddings for texts.

        Args:
            texts: List of texts
            use_cache: Whether to use cache

        Returns:
            Array of embeddings (N x D)
        """
        if not texts:
            return np.array([])

        embeddings = [None] * len(texts)
        texts_to_encode = []
        text_indices = []

        # Check cache
        for i, text in enumerate(texts):
            if use_cache and self.cache_dir:
                cache_key = self._get_cache_key(text)
                cached_emb = self._load_from_cache(cache_key)

                if cached_emb is not None:
                    embeddings[i] = cached_emb
                    continue

            # Need to encode
            texts_to_encode.append(text)
            text_indices.append(i)

        # Encode texts not in cache
        if texts_to_encode:
            logger.info(
                f"Encoding {len(texts_to_encode)} texts "
                f"(cached: {len(texts) - len(texts_to_encode)})"
            )

            # For E5 models, add instruction prefix
            if "e5" in self.model_name.lower():
                texts_to_encode_processed = [f"passage: {text}" for text in texts_to_encode]
            else:
                texts_to_encode_processed = texts_to_encode

            # Encode in batches
            new_embeddings = self.model.encode(
                texts_to_encode_processed,
                batch_size=self.batch_size,
                show_progress_bar=len(texts_to_encode) > 100,
                normalize_embeddings=self.normalize,
                convert_to_numpy=True,
            )

            # Save to cache and add to results
            for i, emb in enumerate(new_embeddings):
                original_idx = text_indices[i]
                original_text = texts[original_idx]

                if use_cache and self.cache_dir:
                    cache_key = self._get_cache_key(original_text)
                    self._save_to_cache(cache_key, emb)

                embeddings[original_idx] = emb

        # Convert to array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Additional normalization if needed and not already done
        if self.normalize and "e5" not in self.model_name.lower():
            norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            embeddings_array = embeddings_array / (norms + 1e-8)

        return embeddings_array

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for query.

        Args:
            query: Query text

        Returns:
            Query embedding (1 x D)
        """
        # For E5 models, add query prefix
        if "e5" in self.model_name.lower():
            query = f"query: {query}"

        embedding = self.model.encode(
            [query],
            batch_size=1,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )

        return embedding[0]

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
