#!/bin/bash
set -e

echo "Starting AgendaFlow..."

# Check if index exists
if [ ! -f "data/index/faiss/index.faiss" ]; then
    echo "Index not found. Building index..."
    python scripts/build_index.py
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to build index"
        exit 1
    fi
    
    echo "Index built successfully"
else
    echo "Index found, skipping build"
fi

# Execute the command passed to the container
exec "$@"
