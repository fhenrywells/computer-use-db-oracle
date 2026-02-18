#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main"
OUT_DIR="data/raw/amazon-reviews-2023"

FILES=(
  "README.md"
  "all_categories.txt"
  "raw/meta_categories/meta_All_Beauty.jsonl"
  "raw/meta_categories/meta_Appliances.jsonl"
  "raw/meta_categories/meta_Video_Games.jsonl"
  "raw/meta_categories/meta_Health_and_Personal_Care.jsonl"
)

mkdir -p "${OUT_DIR}/raw/meta_categories"

for file in "${FILES[@]}"; do
  echo "Downloading ${file}"
  curl -L --retry 3 --fail -C - "${BASE_URL}/${file}" -o "${OUT_DIR}/${file}"
done

echo "Done. Files downloaded to ${OUT_DIR}"
