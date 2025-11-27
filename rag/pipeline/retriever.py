"""Document retriever with MMR."""

from datetime import datetime
from typing import List, Optional
import logging

import numpy as np
from langchain_core.documents import Document

from ..index.faiss_index import FAISSIndexManager

logger = logging.getLogger(__name__)


class EventRetriever:
    """Retrieve relevant events with filtering and MMR."""

    def __init__(
        self,
        index_manager: FAISSIndexManager,
        k_initial: int = 12,
        k_final: int = 5,
        mmr_diversity: float = 0.3,
    ):
        """Initialize retriever.

        Args:
            index_manager: FAISS index manager
            k_initial: Initial number of results to retrieve
            k_final: Final number of results after MMR
            mmr_diversity: Diversity parameter for MMR (0-1, higher = more diverse)
        """
        self.index_manager = index_manager
        self.k_initial = k_initial
        self.k_final = k_final
        self.mmr_diversity = mmr_diversity

    def _filter_by_metadata(
        self,
        documents: List[Document],
        city: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        price_constraint: Optional[str] = None,
        arrondissement: Optional[int] = None,
    ) -> List[Document]:
        """Filter documents by metadata.

        Args:
            documents: List of documents
            city: City filter
            start_date: Start date filter (UTC)
            end_date: End date filter (UTC)
            category: Category filter
            price_constraint: Price constraint ('free', 'cheap')
            arrondissement: Arrondissement number

        Returns:
            Filtered documents
        """
        filtered = []

        for doc in documents:
            metadata = doc.metadata

            # City filter
            if city and metadata.get("city") != city:
                continue

            # Date filter
            if start_date or end_date:
                try:
                    event_start = datetime.fromisoformat(metadata.get("start_datetime"))

                    if start_date and event_start < start_date:
                        continue
                    if end_date and event_start >= end_date:
                        continue
                except (ValueError, TypeError):
                    # Skip if date parsing fails
                    continue

            # Category filter
            if category:
                doc_category = metadata.get("category_norm")
                doc_categories = metadata.get("categories", [])

                if doc_category != category and category not in [c.lower() for c in doc_categories]:
                    continue

            # Price filter
            if price_constraint == "free":
                if not metadata.get("is_free", False):
                    continue
            elif price_constraint == "cheap":
                price_bucket = metadata.get("price_bucket")
                if not (metadata.get("is_free", False) or price_bucket in ["free", "low"]):
                    continue

            # Arrondissement filter
            if arrondissement:
                doc_arr = metadata.get("arrondissement")
                if doc_arr != f"{arrondissement}e":
                    continue

            filtered.append(doc)

        return filtered

    def _apply_mmr(
        self,
        query_embedding: np.ndarray,
        documents: List[Document],
        embeddings: List[np.ndarray],
        k: int,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """Apply Maximal Marginal Relevance.

        Args:
            query_embedding: Query embedding
            documents: Candidate documents
            embeddings: Document embeddings
            k: Number of results to return
            lambda_mult: Balance between relevance and diversity (0-1)

        Returns:
            Re-ranked documents
        """
        if len(documents) <= k:
            return documents

        # Compute similarities to query
        query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        doc_embeddings = np.array(embeddings)
        doc_embeddings = doc_embeddings / (
            np.linalg.norm(doc_embeddings, axis=1, keepdims=True) + 1e-8
        )

        query_similarities = np.dot(doc_embeddings, query_embedding)

        # MMR algorithm
        selected_indices = []
        remaining_indices = list(range(len(documents)))

        # Select first document (highest query similarity)
        first_idx = int(np.argmax(query_similarities))
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)

        # Select remaining documents
        for _ in range(min(k - 1, len(remaining_indices))):
            mmr_scores = []

            for idx in remaining_indices:
                # Relevance score
                relevance = query_similarities[idx]

                # Max similarity to already selected documents
                max_sim_to_selected = max(
                    np.dot(doc_embeddings[idx], doc_embeddings[sel_idx])
                    for sel_idx in selected_indices
                )

                # MMR score
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_sim_to_selected
                mmr_scores.append((idx, mmr_score))

            # Select document with highest MMR score
            best_idx = max(mmr_scores, key=lambda x: x[1])[0]
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        return [documents[i] for i in selected_indices]

    def _check_venue_diversity(self, documents: List[Document]) -> bool:
        """Check if results have venue diversity.

        Args:
            documents: Retrieved documents

        Returns:
            True if diverse, False if too concentrated
        """
        if len(documents) <= 2:
            return True

        # Count events by venue
        venue_counts = {}
        for doc in documents:
            venue = doc.metadata.get("venue_name", "")
            date = doc.metadata.get("start_datetime", "")
            key = f"{venue}_{date}"
            venue_counts[key] = venue_counts.get(key, 0) + 1

        # Check if more than half are at same venue/date
        max_count = max(venue_counts.values())
        return max_count <= len(documents) // 2

    def retrieve(
        self,
        query: str,
        city: Optional[str] = "Paris",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        price_constraint: Optional[str] = None,
        arrondissement: Optional[int] = None,
    ) -> List[Document]:
        """Retrieve relevant events.

        Args:
            query: Query text
            city: City filter
            start_date: Start date filter (UTC)
            end_date: End date filter (UTC)
            category: Category filter
            price_constraint: Price constraint
            arrondissement: Arrondissement number

        Returns:
            List of relevant documents
        """
        # Initial search
        logger.info(f"Searching for: {query}")
        results = self.index_manager.search(query, k=self.k_initial)

        if not results:
            logger.warning("No results found")
            return []

        documents = [doc for doc, _ in results]

        # Apply metadata filters
        filtered_docs = self._filter_by_metadata(
            documents,
            city=city,
            start_date=start_date,
            end_date=end_date,
            category=category,
            price_constraint=price_constraint,
            arrondissement=arrondissement,
        )

        if not filtered_docs:
            logger.warning("No results after filtering")
            return []

        logger.info(f"Found {len(filtered_docs)} results after filtering")

        # If we have enough results, apply MMR for diversity
        if len(filtered_docs) > self.k_final:
            # Get embeddings for filtered documents
            texts = [doc.page_content for doc in filtered_docs]
            doc_embeddings = self.index_manager.embedding_generator.embed_texts(
                texts, use_cache=True
            )

            # Get query embedding
            query_embedding = self.index_manager.embedding_generator.embed_query(query)

            # Apply MMR
            filtered_docs = self._apply_mmr(
                query_embedding,
                filtered_docs,
                doc_embeddings,
                k=self.k_final,
                lambda_mult=1 - self.mmr_diversity,
            )

            logger.info(f"Applied MMR, returning {len(filtered_docs)} results")

        # Check venue diversity
        if not self._check_venue_diversity(filtered_docs[:5]):
            logger.info("Low venue diversity detected")

        return filtered_docs[: self.k_final]
