#!/bin/bash
echo "--- Creating Cache Directories ---"
mkdir -p model_cache/ollama
mkdir -p model_cache/huggingface
mkdir -p model_cache/nltk

echo "--- Pulling Ollama Model (Gemma:2b) ---"
# Temporarily start ollama to pull the model to our local volume
docker run --rm -v $(pwd)/model_cache/ollama:/root/.ollama ollama/ollama:latest pull gemma:2b

echo "--- Setup Complete. You can now run docker compose! ---"