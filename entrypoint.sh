#!/bin/bash
set -e

echo "=== EIP Navigator Docker Entrypoint ==="

# Check if data needs to be fetched
if [ ! -d "/app/data" ] || [ -z "$(ls -A /app/data 2>/dev/null)" ]; then
    echo "[1/3] Fetching ERC documents..."
    python fetch_docs.py
else
    echo "[1/3] Data directory already populated, skipping fetch."
fi

# Check if ingestion is needed
if [ ! -f "/app/bm25_index.pkl" ] || [ ! -d "/app/chroma_db" ]; then
    echo "[2/3] Running ingestion pipeline..."
    python ingest.py
else
    echo "[2/3] Indexes already exist, skipping ingestion."
fi

echo "[3/3] Starting server..."
exec uvicorn main:app --host 0.0.0.0 --port 8123
