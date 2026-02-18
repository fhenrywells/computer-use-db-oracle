#!/usr/bin/env bash
set -euo pipefail
echo "Starting Mongo..."
docker compose up -d mongo
echo "Bootstrap complete."

