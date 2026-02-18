# Amazon-Reviews-2023 Selection

Source dataset:
- https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

Downloaded item metadata subset for the fake storefront:
- `raw/meta_categories/meta_All_Beauty.jsonl` (~209 MB)
- `raw/meta_categories/meta_Appliances.jsonl` (~272 MB)
- `raw/meta_categories/meta_Video_Games.jsonl` (~432 MB)
- `raw/meta_categories/meta_Health_and_Personal_Care.jsonl` (~128 MB)

Support files:
- `README.md` (dataset card)
- `all_categories.txt`
- `manifest.json` (Hugging Face dataset API response snapshot)

Re-download command:

```bash
./scripts/download_amazon_reviews_2023_subset.sh
```
