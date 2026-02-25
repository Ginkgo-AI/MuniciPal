#!/usr/bin/env bash
set -euo pipefail

# Munici-Pal Phase 0 Infrastructure Setup
# Stands up the local LLM runtime and vector DB

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MODEL="${MUNICIPAL_LLM_MODEL:-llama3.1:8b}"

echo "=== Munici-Pal Infrastructure Setup ==="
echo "Project: $PROJECT_DIR"
echo "Model:   $MODEL"
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose is required"; exit 1; }

# Start services
echo "--- Starting Ollama and ChromaDB ---"
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

# Wait for Ollama to be ready
echo "--- Waiting for Ollama ---"
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Ollama did not start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Pull model
echo "--- Pulling model: $MODEL ---"
docker exec municipal-ollama ollama pull "$MODEL"

# Wait for ChromaDB
echo "--- Waiting for ChromaDB ---"
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/v1/heartbeat >/dev/null 2>&1; then
        echo "ChromaDB is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: ChromaDB did not start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Verify
echo ""
echo "=== Infrastructure Ready ==="
echo "Ollama:   http://localhost:11434"
echo "ChromaDB: http://localhost:8000"
echo "Model:    $MODEL"
echo ""
echo "Run 'python scripts/run_eval.py --dataset eval/golden_datasets/sample.json' to test."
