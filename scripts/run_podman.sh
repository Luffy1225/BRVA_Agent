#!/bin/bash
# ==========================================================
# BRVA AeroAgent Podman Execution Helper Script
# For Professor / TA Evaluation & Cross-Platform Verification
# ==========================================================

set -e

IMAGE_NAME="aeroagent:v1"
CONTAINER_NAME="aeroagent-app"

echo "=========================================================="
echo "✈️  BRVA AeroAgent - Podman Engine Execution Helper"
echo "=========================================================="

CONTAINER_ENGINE=""
if command -v podman &> /dev/null; then
    CONTAINER_ENGINE="podman"
elif command -v docker &> /dev/null; then
    CONTAINER_ENGINE="docker"
else
    echo "❌ Error: Neither 'podman' nor 'docker' engine was found on PATH."
    echo "Please install Podman: https://podman.io/"
    exit 1
fi

echo "🐳 Using Container Engine: $CONTAINER_ENGINE"

MODE="${1:---web}"

case "$MODE" in
    --build)
        echo "🔨 Building image $IMAGE_NAME..."
        $CONTAINER_ENGINE build -t $IMAGE_NAME .
        echo "✅ Build completed successfully."
        ;;
    --cli)
        echo "🚀 Launching AeroAgent in Interactive CLI Mode..."
        if ! $CONTAINER_ENGINE image inspect $IMAGE_NAME &> /dev/null; then
            echo "Image $IMAGE_NAME not found. Building first..."
            $CONTAINER_ENGINE build -t $IMAGE_NAME .
        fi
        $CONTAINER_ENGINE run -it --rm $IMAGE_NAME python -m src.ui.cli
        ;;
    --test)
        echo "🧪 Running Automated Verification & Benchmark inside Container..."
        if ! $CONTAINER_ENGINE image inspect $IMAGE_NAME &> /dev/null; then
            echo "Image $IMAGE_NAME not found. Building first..."
            $CONTAINER_ENGINE build -t $IMAGE_NAME .
        fi
        echo "--- 1. Full Unit Test Suite (105 Tests) ---"
        $CONTAINER_ENGINE run --rm $IMAGE_NAME python -m unittest discover tests -p "test_*.py"
        echo "--- 2. End-to-End Demo Scenarios (14 Scenarios) ---"
        $CONTAINER_ENGINE run --rm $IMAGE_NAME python scripts/demo_test_suite.py
        echo "✅ All Container Test Benchmarks PASSED 100%!"
        ;;
    --web|*)
        echo "🌐 Starting AeroAgent Streamlit Web Dashboard on http://localhost:8501..."
        if ! $CONTAINER_ENGINE image inspect $IMAGE_NAME &> /dev/null; then
            echo "Image $IMAGE_NAME not found. Building first..."
            $CONTAINER_ENGINE build -t $IMAGE_NAME .
        fi
        $CONTAINER_ENGINE rm -f $CONTAINER_NAME 2>/dev/null || true
        $CONTAINER_ENGINE run -d --name $CONTAINER_NAME -p 8501:8501 $IMAGE_NAME
        echo "✅ AeroAgent container is running!"
        echo "👉 Open your browser at: http://localhost:8501"
        echo "To view logs:    $CONTAINER_ENGINE logs -f $CONTAINER_NAME"
        echo "To stop:         $CONTAINER_ENGINE stop $CONTAINER_NAME"
        ;;
esac
