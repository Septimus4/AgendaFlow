# Contributing to AgendaFlow

Thank you for your interest in contributing to AgendaFlow! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- OpenAgenda API key
- Mistral API key

### Setting Up Development Environment

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/AgendaFlow.git
cd AgendaFlow
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
make dev-install
# or
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov black ruff mypy
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys
```

5. **Build the index** (optional, for testing)

```bash
make build-index
# or
python scripts/build_index.py
```

## Development Workflow

### Code Style

We use:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **MyPy** for type checking

Format your code before committing:

```bash
make format
# or
black .
ruff check . --fix
```

### Testing

We aim for high test coverage. Write tests for all new features and bug fixes.

**Run tests:**

```bash
make test
# or
pytest tests/ -v
```

**Run tests with coverage:**

```bash
make test-cov
# or
pytest tests/ --cov=rag --cov=api --cov-report=html
```

**Test structure:**

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for combined functionality
- `tests/evaluation/` - Evaluation tests using Ragas metrics

### Making Changes

1. **Create a new branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make your changes**

- Write clear, concise code
- Add docstrings to functions and classes
- Update documentation as needed
- Add tests for new functionality

3. **Run tests and linting**

```bash
make lint
make test
```

4. **Commit your changes**

Use clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: description of what you added"
```

Follow conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

5. **Push and create a pull request**

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Project Structure

```
AgendaFlow/
├── api/                    # FastAPI application
├── rag/                   # RAG components
│   ├── ingest/            # Data ingestion
│   ├── index/             # Indexing and embeddings
│   └── pipeline/          # RAG pipeline
├── configs/               # Configuration files
├── scripts/               # Utility scripts
├── tests/                 # Tests
├── evaluation/            # Evaluation framework
└── docs/                  # Documentation
```

## Data Handling

The OpenAgenda API can sometimes return inconsistent data types (e.g., strings instead of dictionaries for titles, or integers for IDs that should be strings).

When working on `rag/ingest/`, always ensure robust type checking and error handling. The `EventLoader` and `clean_event` functions are designed to handle these inconsistencies.

## Adding New Features

### Adding a New Data Source

1. Create a new client in `rag/ingest/`
2. Implement the same interface as `OpenAgendaClient`
3. Update `EventLoader` to support the new source
4. Add tests in `tests/unit/test_ingest.py`

### Adding a New Query Filter

1. Update `QueryProcessor` in `rag/pipeline/query_processor.py`
2. Add extraction logic for the new filter
3. Update `EventRetriever` to apply the filter
4. Add tests in `tests/unit/test_query_processor.py`

### Adding New Evaluation Metrics

1. Add test cases to `evaluation/qa.jsonl`
2. Update `evaluation/evaluate.py` to compute new metrics
3. Update thresholds in `configs/config.yaml`

## Documentation

Update documentation when:
- Adding new features
- Changing API endpoints
- Modifying configuration options
- Updating dependencies

Documentation locations:
- `README.md` - Main documentation
- `docs/API.md` - API reference
- `CONTRIBUTING.md` - This file
- Docstrings - In-code documentation

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### PR Description

Include:
- **What**: Description of changes
- **Why**: Reason for changes
- **How**: Implementation approach
- **Testing**: How changes were tested
- **Screenshots**: If UI changes (N/A for this project)

### Review Process

1. Automated checks must pass (CI)
2. At least one maintainer approval required
3. Address review comments
4. Squash commits if requested

## Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Steps to reproduce**: Detailed steps
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Environment**: Python version, OS, etc.
6. **Logs**: Relevant error messages or logs

Use the GitHub issue template.

## Feature Requests

When requesting features, include:

1. **Use case**: Why is this needed?
2. **Proposed solution**: How should it work?
3. **Alternatives**: Other approaches considered
4. **Additional context**: Any other relevant info

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## Questions?

- Open a GitHub issue with the `question` label
- Check existing issues and documentation first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be:
- Listed in the contributors section
- Mentioned in release notes
- Credited in documentation (for significant contributions)

Thank you for contributing! 🎉
