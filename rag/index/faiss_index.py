"""FAISS index builder and manager."""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import faiss
import numpy as np
from langchain_core.documents import Document

from ..ingest.schema import Event
from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class FAISSIndexManager:
    """Manage FAISS index and document store."""

    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        index_path: Path,
        hnsw_m: int = 32,
        hnsw_ef_construction: int = 200,
        hnsw_ef_search: int = 64,
    ):
        """Initialize manager.

        Args:
            embedding_generator: Embedding generator
            index_path: Path to persist index
            hnsw_m: HNSW M parameter
            hnsw_ef_construction: HNSW efConstruction parameter
            hnsw_ef_search: HNSW efSearch parameter
        """
        self.embedding_generator = embedding_generator
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        self.hnsw_m = hnsw_m
        self.hnsw_ef_construction = hnsw_ef_construction
        self.hnsw_ef_search = hnsw_ef_search

        self.index: Optional[faiss.IndexHNSWFlat] = None
        self.docstore: Dict[str, Document] = {}
        self.index_to_docstore_id: Dict[int, str] = {}

    def build_index(self, events: List[Event]) -> Tuple[faiss.IndexHNSWFlat, Dict]:
        """Build FAISS index from events.

        Args:
            events: List of Event objects

        Returns:
            Tuple of (index, docstore)
        """
        if not events:
            raise ValueError("No events to index")

        logger.info(f"Building index for {len(events)} events")

        # Create documents
        documents = []
        for event in events:
            doc = Document(
                page_content=event.get_document_text(),
                metadata=event.get_metadata(),
            )
            documents.append(doc)

        # Generate embeddings
        texts = [doc.page_content for doc in documents]
        logger.info("Generating embeddings...")
        embeddings = self.embedding_generator.embed_texts(texts)

        logger.info(f"Generated {len(embeddings)} embeddings of dimension {embeddings.shape[1]}")

        # Create FAISS index
        dimension = embeddings.shape[1]

        # IndexHNSWFlat uses L2 distance
        index = faiss.IndexHNSWFlat(dimension, self.hnsw_m)
        index.hnsw.efConstruction = self.hnsw_ef_construction

        # Add vectors
        logger.info("Adding vectors to FAISS index...")
        index.add(embeddings)

        logger.info(f"Index built with {index.ntotal} vectors")

        # Create docstore
        docstore = {str(i): doc for i, doc in enumerate(documents)}

        # Create index to docstore mapping
        index_to_docstore_id = {i: str(i) for i in range(len(documents))}

        self.index = index
        self.docstore = docstore
        self.index_to_docstore_id = index_to_docstore_id

        return index, docstore

    def save_index(self, metadata: Optional[Dict] = None):
        """Save index and docstore to disk.

        Args:
            metadata: Optional metadata to save with index
        """
        if self.index is None or self.docstore is None:
            raise ValueError("No index to save")

        logger.info(f"Saving index to {self.index_path}")

        # Save FAISS index
        index_file = self.index_path / "index.faiss"
        faiss.write_index(self.index, str(index_file))

        # Save docstore
        docstore_file = self.index_path / "docstore.pkl"
        with open(docstore_file, "wb") as f:
            pickle.dump(self.docstore, f)

        # Save index mapping
        mapping_file = self.index_path / "index_to_docstore_id.pkl"
        with open(mapping_file, "wb") as f:
            pickle.dump(self.index_to_docstore_id, f)

        # Save manifest
        manifest = {
            "total_documents": self.index.ntotal,
            "dimension": self.index.d,
            "hnsw_m": self.hnsw_m,
            "hnsw_ef_construction": self.hnsw_ef_construction,
            "hnsw_ef_search": self.hnsw_ef_search,
            "embedding_model": self.embedding_generator.model_name,
            "created_at": None,  # Will be set when called
        }

        if metadata:
            manifest.update(metadata)

        # Add timestamp
        from datetime import datetime

        manifest["created_at"] = datetime.utcnow().isoformat()

        manifest_file = self.index_path / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info("Index saved successfully")

    def load_index(self) -> bool:
        """Load index and docstore from disk.

        Returns:
            True if loaded successfully, False otherwise
        """
        index_file = self.index_path / "index.faiss"
        docstore_file = self.index_path / "docstore.pkl"
        mapping_file = self.index_path / "index_to_docstore_id.pkl"
        manifest_file = self.index_path / "manifest.json"

        if not all(f.exists() for f in [index_file, docstore_file, mapping_file, manifest_file]):
            logger.warning(f"Index files not found in {self.index_path}")
            return False

        try:
            logger.info(f"Loading index from {self.index_path}")

            # Load FAISS index
            self.index = faiss.read_index(str(index_file))

            # Set efSearch parameter
            if isinstance(self.index, faiss.IndexHNSWFlat):
                self.index.hnsw.efSearch = self.hnsw_ef_search

            # Load docstore
            with open(docstore_file, "rb") as f:
                self.docstore = pickle.load(f)

            # Load index mapping
            with open(mapping_file, "rb") as f:
                self.index_to_docstore_id = pickle.load(f)

            # Load manifest
            with open(manifest_file, "r") as f:
                manifest = json.load(f)

            logger.info(
                f"Index loaded successfully: "
                f"{manifest.get('total_documents')} documents, "
                f"dimension {manifest.get('dimension')}"
            )

            return True

        except Exception as e:
            logger.error(f"Error loading index: {e}", exc_info=True)
            return False

    def search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """Search index for similar documents.

        Args:
            query: Query text
            k: Number of results to return

        Returns:
            List of (document, distance) tuples
        """
        if self.index is None or self.docstore is None:
            raise ValueError("Index not loaded")

        # Generate query embedding
        query_embedding = self.embedding_generator.embed_query(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        # Search
        distances, indices = self.index.search(query_embedding, k)

        # Retrieve documents
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # FAISS returns -1 for empty results
                continue

            doc_id = self.index_to_docstore_id.get(int(idx))
            if doc_id and doc_id in self.docstore:
                doc = self.docstore[doc_id]
                # Convert L2 distance to similarity score
                # Lower distance = higher similarity
                similarity = 1.0 / (1.0 + distance)
                results.append((doc, similarity))

        return results
