#!/usr/bin/env python3
"""Quick start script for AgendaFlow."""

import sys
import os
from pathlib import Path

print("=" * 60)
print("AgendaFlow Quick Start")
print("=" * 60)
print()

# Check if .env exists
env_file = Path(".env")
if not env_file.exists():
    print("❌ .env file not found!")
    print()
    print("Please create a .env file with your API keys:")
    print("  1. Copy .env.example to .env")
    print("  2. Edit .env and add your API keys:")
    print("     - MISTRAL_API_KEY")
    print("     - OPENAGENDA_API_KEY")
    print()
    print("Example:")
    print("  $ cp .env.example .env")
    print("  $ nano .env  # or use your favorite editor")
    print()
    sys.exit(1)

# Check if required environment variables are set
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

mistral_key = os.getenv("MISTRAL_API_KEY")
openagenda_key = os.getenv("OPENAGENDA_API_KEY")

if not mistral_key or mistral_key == "your_mistral_api_key_here":
    print("❌ MISTRAL_API_KEY not set properly!")
    print("Please edit .env and add your Mistral API key")
    print()
    sys.exit(1)

if not openagenda_key or openagenda_key == "your_openagenda_api_key_here":
    print("❌ OPENAGENDA_API_KEY not set properly!")
    print("Please edit .env and add your OpenAgenda API key")
    print()
    sys.exit(1)

print("✓ Environment configured")
print()

# Check if index exists
index_file = Path("data/index/faiss/index.faiss")
if not index_file.exists():
    print("⚠️  Index not found")
    print()
    print("Building index from OpenAgenda data...")
    print("This may take several minutes...")
    print()

    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/build_index.py"],
        capture_output=False,
    )

    if result.returncode != 0:
        print()
        print("❌ Index build failed!")
        print("Please check the error messages above")
        sys.exit(1)

    print()
    print("✓ Index built successfully")
    print()
else:
    print("✓ Index found")
    print()

print("=" * 60)
print("Ready to start!")
print("=" * 60)
print()
print("Run the following command to start the API server:")
print()
print("  uvicorn api.main:app --host 0.0.0.0 --port 8000")
print()
print("Or use the Makefile:")
print()
print("  make run")
print()
print("The API will be available at:")
print("  - http://localhost:8000")
print("  - Docs: http://localhost:8000/docs")
print()
print("Example query:")
print("  curl -X POST http://localhost:8000/ask \\")
print('    -H "Content-Type: application/json" \\')
print('    -d \'{"question": "Quels concerts ce week-end ?"}\'')
print()
