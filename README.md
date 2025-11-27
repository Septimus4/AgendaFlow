# AgendaFlow

A self-contained RAG (Retrieval-Augmented Generation) service that answers event-related questions for Paris using OpenAgenda data.

## Features

- **Geographic Focus**: Paris city limits for maximum event density
- **Data Source**: OpenAgenda API with fallback support
- **Multilingual**: Supports French and English queries and answers
- **Fast Retrieval**: FAISS CPU with HNSW for approximate nearest neighbor search
- **Smart Query Understanding**: Temporal parsing, category extraction, price filtering
- **LLM-Powered Answers**: Mistral AI for natural language responses
- **Production-Ready**: FastAPI service with health checks, metrics, and Docker support

## Architecture

```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Query Processor                        │
│  - Language detection                   │
│  - Temporal parsing                     │
│  - Constraint extraction                │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Retriever (FAISS + MMR)                │
│  - Vector search                        │
│  - Metadata filtering                   │
│  - Diversity re-ranking                 │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Answer Generator (Mistral LLM)        │
│  - Context formatting                   │
│  - Answer synthesis                     │
│  - Structured output                    │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Response       │
└─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAgenda API key ([get one here](https://developers.openagenda.com/))
- Mistral API key ([get one here](https://docs.mistral.ai/))

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/Septimus4/AgendaFlow.git
cd AgendaFlow
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
OPENAGENDA_API_KEY=your_openagenda_api_key_here
RAG_MODEL_NAME=mistral-small-latest
REBUILD_TOKEN=your_secure_token_here
```

5. **Build the index**

```bash
python scripts/build_index.py
```

This will:
- Fetch events from OpenAgenda for Paris (last 365 days + upcoming)
- Clean and normalize the data
- Generate embeddings using multilingual-e5-base
- Build and persist the FAISS index

6. **Start the service**

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your API keys
```

2. **Start the service**

```bash
docker-compose up -d
```

The service will:
- Build the Docker image
- Automatically build the index on first run
- Start the API server on port 8000

3. **View logs**

```bash
docker-compose logs -f
```

### Using Docker directly

```bash
# Build image
docker build -t agendaflow:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e MISTRAL_API_KEY=your_key \
  -e OPENAGENDA_API_KEY=your_key \
  --name agendaflow \
  agendaflow:latest
```

## Documentation

- [User Guide](docs/USER_GUIDE.md): Detailed usage instructions and query examples.
- [Architecture](docs/ARCHITECTURE.md): System design, component details, and technical decisions.
- [API Documentation](docs/API.md): Technical API reference.
- [Postman Collection](docs/AgendaFlow.postman_collection.json): Ready-to-use collection for API testing.
- [Contributing Guide](CONTRIBUTING.md): Instructions for developers.

## Configuration

Configuration is managed through environment variables (`.env`) and `configs/config.yaml`.

### Key Configuration Options

- **RAG_MODEL_NAME**: Mistral model (default: mistral-small-latest)
- **OPENAGENDA_MODE**: Data fetch mode (agenda, transverse, fallback_odsd)
- **K_INITIAL**: Initial retrieval count (default: 12)
- **K_FINAL**: Final results after MMR (default: 5)
- **MMR_DIVERSITY**: Diversity parameter (default: 0.3)

## Development

### Running Tests

```bash
pytest tests/
```

### Linting

```bash
# Black formatting
black .

# Ruff linting
ruff check .
```

### Type Checking

```bash
mypy api/ rag/
```

## Performance

- **Latency**: p50 ≤ 1.5s with warm index (single worker, CPU)
- **Index Build**: ~5 minutes for 5000 events on laptop
- **Memory**: ~2GB with loaded index

## Project Structure

```
AgendaFlow/
├── api/                    # FastAPI application
│   ├── config.py          # Configuration
│   ├── main.py            # API endpoints
│   └── models.py          # Request/response models
├── rag/                   # RAG components
│   ├── ingest/            # Data ingestion
│   │   ├── cleaning.py    # Data cleaning
│   │   ├── deduplication.py
│   │   ├── loader.py      # Event loader
│   │   ├── openagenda_client.py
│   │   └── schema.py      # Event schema
│   ├── index/             # Indexing
│   │   ├── embeddings.py  # Embedding generation
│   │   └── faiss_index.py # FAISS index manager
│   └── pipeline/          # RAG pipeline
│       ├── generator.py   # Answer generation
│       ├── query_processor.py
│       ├── rag_pipeline.py
│       └── retriever.py   # Document retrieval
├── configs/               # Configuration files
├── scripts/               # Utility scripts
├── tests/                 # Tests
├── evaluation/            # Evaluation framework
├── docs/                  # Documentation
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:

- GitHub Issues: https://github.com/Septimus4/AgendaFlow/issues
- OpenAgenda API Docs: https://developers.openagenda.com/
- Mistral AI Docs: https://docs.mistral.ai/

## Acknowledgments

- OpenAgenda for event data
- Mistral AI for LLM capabilities
- LangChain for RAG framework
- FAISS for vector search
