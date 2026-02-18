#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient


def _top_terms(col, field: str, limit: int) -> list[dict]:
    pipeline = [
        {"$match": {field: {"$type": "string", "$ne": ""}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": limit},
    ]
    return [{"value": d["_id"], "count": d["count"]} for d in col.aggregate(pipeline)]


def _price_buckets(col) -> list[dict]:
    boundaries = [0, 10, 25, 50, 100, 250, 500, 1000, 5000]
    pipeline = [
        {"$match": {"price": {"$type": "number", "$gte": 0}}},
        {
            "$bucket": {
                "groupBy": "$price",
                "boundaries": boundaries,
                "default": "5000+",
                "output": {"count": {"$sum": 1}},
            }
        },
    ]
    rows = list(col.aggregate(pipeline))
    out = []
    for row in rows:
        bucket = row["_id"]
        if isinstance(bucket, (int, float)):
            idx = boundaries.index(bucket)
            right = boundaries[idx + 1]
            label = f"[{int(bucket)}, {int(right)})"
        else:
            label = str(bucket)
        out.append({"value": label, "count": row["count"]})
    return out


def _rating_buckets(col) -> list[dict]:
    pipeline = [
        {"$match": {"rating_avg": {"$type": "number", "$gte": 0}}},
        {
            "$project": {
                "bucket": {
                    "$switch": {
                        "branches": [
                            {"case": {"$lt": ["$rating_avg", 1]}, "then": "<1"},
                            {"case": {"$lt": ["$rating_avg", 2]}, "then": "[1,2)"},
                            {"case": {"$lt": ["$rating_avg", 3]}, "then": "[2,3)"},
                            {"case": {"$lt": ["$rating_avg", 4]}, "then": "[3,4)"},
                            {"case": {"$lt": ["$rating_avg", 4.5]}, "then": "[4,4.5)"},
                        ],
                        "default": "[4.5,5]",
                    }
                }
            }
        },
        {"$group": {"_id": "$bucket", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]
    return [{"value": d["_id"], "count": d["count"]} for d in col.aggregate(pipeline)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build facet stats for storefront defaults.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", default="simazon")
    parser.add_argument("--collection", default="products")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--out", default="data/processed/facet_stats.json")
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    try:
        col = client[args.db][args.collection]
        stats = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db": args.db,
            "collection": args.collection,
            "document_count": col.count_documents({}),
            "top_k": args.top_k,
            "facets": {
                "brand": _top_terms(col, "brand", args.top_k),
                "category_leaf": _top_terms(col, "category_leaf", args.top_k),
                "price_bucket": _price_buckets(col),
                "rating_bucket": _rating_buckets(col),
            },
        }
    finally:
        client.close()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"wrote facet stats: {out_path}")
    print(f"documents: {stats['document_count']}")
    print(f"top brands: {len(stats['facets']['brand'])}")
    print(f"top categories: {len(stats['facets']['category_leaf'])}")


if __name__ == "__main__":
    main()
