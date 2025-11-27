"""Unit tests for RAG components."""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from langchain_core.documents import Document
from datetime import datetime

from rag.index.embeddings import EmbeddingGenerator
from rag.pipeline.retriever import EventRetriever
from rag.pipeline.generator import AnswerGenerator


class TestEmbeddingGenerator(unittest.TestCase):
    """Test EmbeddingGenerator."""

    @patch("rag.index.embeddings.SentenceTransformer")
    def test_embed_texts(self, mock_transformer):
        """Test text embedding generation."""
        # Setup mock
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_transformer.return_value = mock_model

        # Initialize generator
        generator = EmbeddingGenerator(model_name="test-model", cache_dir=None)

        # Test embedding
        texts = ["text1", "text2"]
        embeddings = generator.embed_texts(texts, use_cache=False)

        # Verify
        self.assertEqual(embeddings.shape, (2, 2))
        mock_model.encode.assert_called_once()

    @patch("rag.index.embeddings.SentenceTransformer")
    def test_embed_query(self, mock_transformer):
        """Test query embedding generation."""
        # Setup mock
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        mock_transformer.return_value = mock_model

        # Initialize generator
        generator = EmbeddingGenerator(model_name="test-model", cache_dir=None)

        # Test embedding
        query = "test query"
        embedding = generator.embed_query(query)

        # Verify
        self.assertEqual(embedding.shape, (2,))
        mock_model.encode.assert_called_once()


class TestEventRetriever(unittest.TestCase):
    """Test EventRetriever."""

    def setUp(self):
        """Setup test fixtures."""
        self.mock_index_manager = MagicMock()
        self.retriever = EventRetriever(
            index_manager=self.mock_index_manager,
            k_initial=10,
            k_final=5
        )

    def test_filter_by_metadata(self):
        """Test metadata filtering."""
        # Create test documents
        docs = [
            Document(
                page_content="doc1",
                metadata={
                    "city": "Paris",
                    "start_datetime": "2025-01-01T10:00:00",
                    "is_free": True,
                    "arrondissement": "11e"
                }
            ),
            Document(
                page_content="doc2",
                metadata={
                    "city": "Lyon",
                    "start_datetime": "2025-01-01T10:00:00",
                    "is_free": False
                }
            )
        ]

        # Test city filter
        filtered = self.retriever._filter_by_metadata(docs, city="Paris")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].page_content, "doc1")

        # Test price filter
        filtered = self.retriever._filter_by_metadata(docs, price_constraint="free")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].page_content, "doc1")

    def test_retrieve(self):
        """Test retrieval flow."""
        # Setup mock results
        mock_docs = [
            (Document(page_content="doc1", metadata={"city": "Paris"}), 0.9),
            (Document(page_content="doc2", metadata={"city": "Paris"}), 0.8)
        ]
        self.mock_index_manager.search.return_value = mock_docs
        
        # Mock embedding generator for MMR
        self.mock_index_manager.embedding_generator.embed_texts.return_value = np.array([[0.1], [0.2]])
        self.mock_index_manager.embedding_generator.embed_query.return_value = np.array([0.15])

        # Test retrieve
        results = self.retriever.retrieve("query")

        # Verify
        self.assertEqual(len(results), 2)
        self.mock_index_manager.search.assert_called_once()


class TestAnswerGenerator(unittest.TestCase):
    """Test AnswerGenerator."""

    @patch("rag.pipeline.generator.ChatMistralAI")
    def test_generate(self, mock_mistral):
        """Test answer generation."""
        # Setup mock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Generated answer"
        mock_llm.invoke.return_value = mock_response
        mock_mistral.return_value = mock_llm

        # Initialize generator
        generator = AnswerGenerator(api_key="test-key")

        # Create test documents
        docs = [
            Document(
                page_content="Event description",
                metadata={
                    "title": "Event 1",
                    "start_datetime": "2025-01-01T20:00:00",
                    "venue_name": "Venue 1",
                    "city": "Paris"
                }
            )
        ]

        # Test generate
        result = generator.generate("query", docs)

        # Verify
        self.assertEqual(result["answer"], "Generated answer")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["title"], "Event 1")
        mock_llm.invoke.assert_called_once()

    def test_generate_no_docs(self):
        """Test generation with no documents."""
        generator = AnswerGenerator(api_key="test-key")
        
        result = generator.generate("query", [])
        
        self.assertIn("Je n'ai pas trouvé d'événements", result["answer"])
        self.assertEqual(len(result["events"]), 0)

if __name__ == "__main__":
    unittest.main()
